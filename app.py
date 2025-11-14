from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
import config, os, smtplib, json, logging
from email.message import EmailMessage

app = Flask(__name__)
app.config.from_object('config')
app.secret_key = app.config.get('SECRET_KEY') or 'change-this'

db = SQLAlchemy(app)
log = logging.getLogger('app')

# Models
class Stylist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    start_hour = db.Column(db.Integer, default=9)
    end_hour = db.Column(db.Integer, default=17)
    work_days = db.Column(db.String(120), default='Mon,Tue,Wed,Thu,Fri')

    def to_dict(self):
        return {'id':self.id,'name':self.name,'start_hour':self.start_hour,'end_hour':self.end_hour,'work_days':self.work_days}

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, default=0)
    def to_dict(self):
        return {'id':self.id,'name':self.name,'duration_minutes':self.duration_minutes,'price':self.price}

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(40), nullable=True)
    client_email = db.Column(db.String(120), nullable=True)
    stylist_id = db.Column(db.Integer, db.ForeignKey('stylist.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default='confirmed')

# Create tables on first request (avoids Render startup timeout)
@app.before_first_request
def create_tables():
    db.create_all()
    # seed if empty
    if not Service.query.first():
        s1 = Service(name='Hajvágás', duration_minutes=30, price=8000)
        s2 = Service(name='Festés', duration_minutes=90, price=20000)
        s3 = Service(name='Borotválás', duration_minutes=20, price=5000)
        db.session.add_all([s1,s2,s3])
    if not Stylist.query.first():
        st1 = Stylist(name='Fodrász A', start_hour=9, end_hour=17)
        st2 = Stylist(name='Fodrász B', start_hour=10, end_hour=15)
        db.session.add_all([st1,st2])
    db.session.commit()

# --- Helpers ---
def send_email(to_email, subject, body):
    if not app.config.get('SMTP_USER') or not app.config.get('SMTP_PASS'):
        log.info('SMTP credentials not configured; skipping email.')
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = app.config.get('FROM_EMAIL') or app.config.get('SMTP_USER')
        msg['To'] = to_email
        msg.set_content(body)
        with smtplib.SMTP(app.config.get('SMTP_HOST'), app.config.get('SMTP_PORT')) as smtp:
            smtp.starttls()
            smtp.login(app.config.get('SMTP_USER'), app.config.get('SMTP_PASS'))
            smtp.send_message(msg)
        return True
    except Exception as e:
        log.error('Email error: %s', e)
        return False

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

def booking_conflict(stylist_id, start_dt, end_dt):
    # check overlapping bookings for same stylist
    conflicts = Booking.query.filter(Booking.stylist_id==stylist_id,
                                     Booking.start_datetime < end_dt,
                                     Booking.end_datetime > start_dt).count()
    return conflicts > 0

# Google Calendar integration (optional stub)
def create_gcal_event(booking):
    if not app.config.get('GCAL_ENABLED'):
        log.info('GCal disabled.')
        return False
    # Place for full integration using google-api-python-client and OAuth/service account.
    # For now, just log and return False (user can extend with credentials).
    log.info('GCal event placeholder for booking %s', booking.id)
    return False

# --- Routes ---
@app.route('/')
def index():
    services = [s.to_dict() for s in Service.query.order_by(Service.name).all()]
    stylists = [s.to_dict() for s in Stylist.query.order_by(Stylist.name).all()]
    return render_template('index.html', services=services, stylists=stylists, title='San Jose Barber')

@app.route('/api/availability')
def availability():
    stylist_id = request.args.get('stylist')
    date_str = request.args.get('date')
    service_id = request.args.get('service')
    if not stylist_id or not date_str:
        return jsonify({'error':'missing params'}), 400
    try:
        stylist_id = int(stylist_id)
        date_obj = datetime.fromisoformat(date_str).date()
    except Exception:
        return jsonify({'error':'invalid params'}), 400
    stylist = Stylist.query.get(stylist_id)
    if not stylist:
        return jsonify({'error':'no such stylist'}), 404
    service = Service.query.get(int(service_id)) if service_id else None
    duration = timedelta(minutes=service.duration_minutes) if service else timedelta(minutes=30)
    step = timedelta(minutes=15)
    current = datetime.combine(date_obj, time(hour=stylist.start_hour, minute=0))
    end_of_day = datetime.combine(date_obj, time(hour=stylist.end_hour, minute=0))
    bookings = Booking.query.filter(Booking.stylist_id==stylist_id,
                                     Booking.start_datetime >= current,
                                     Booking.start_datetime < end_of_day).all()
    slots = []
    while current + duration <= end_of_day:
        free = True
        for b in bookings:
            if overlaps(current, current+duration, b.start_datetime, b.end_datetime):
                free = False
                break
        slots.append({'start': current.isoformat(), 'free': free})
        current += step
    return jsonify({'slots': slots})

@app.route('/book', methods=['POST'])
def book_post():
    data = request.json or {}
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    stylist_id = int(data.get('stylist'))
    service_id = int(data.get('service'))
    start_iso = data.get('start')
    try:
        start_dt = datetime.fromisoformat(start_iso)
    except Exception:
        return jsonify({'error':'invalid start'}), 400
    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error':'service not found'}), 400
    end_dt = start_dt + timedelta(minutes=service.duration_minutes)
    # conflict check
    if booking_conflict(stylist_id, start_dt, end_dt):
        return jsonify({'error':'conflict'}), 409
    booking = Booking(client_name=name, client_phone=phone, client_email=email,
                      stylist_id=stylist_id, service_id=service_id,
                      start_datetime=start_dt, end_datetime=end_dt)
    db.session.add(booking)
    db.session.commit()
    # send emails
    if email:
        send_email(email, 'Foglalás visszaigazolás', f'Kedves {name},\n\nSikeresen lefoglaltad: {start_dt} - {service.name}')
    admin_email = app.config.get('ADMIN_EMAIL')
    if admin_email:
        send_email(admin_email, 'Új foglalás', f'Új foglalás: {name} - {service.name} - {start_dt} - Tel: {phone}')
    # optionally create GCal event (stub)
    create_gcal_event(booking)
    return jsonify({'ok': True})

# --- Admin (password protected via session) ---
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw and pw == app.config.get('ADMIN_PASSWORD'):
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Hibás jelszó','error')
    return render_template('admin_login.html', title='Admin login')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    stylists = Stylist.query.order_by(Stylist.name).all()
    services = Service.query.order_by(Service.name).all()
    bookings = Booking.query.order_by(Booking.start_datetime.desc()).all()
    return render_template('admin_dashboard.html', stylists=stylists, services=services, bookings=bookings)

@app.route('/admin/stylist/add', methods=['POST'])
def admin_add_stylist():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    name = request.form.get('name'); start = int(request.form.get('start_hour',9)); end = int(request.form.get('end_hour',17))
    days = request.form.get('work_days','Mon,Tue,Wed,Thu,Fri')
    s = Stylist(name=name,start_hour=start,end_hour=end,work_days=days)
    db.session.add(s); db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/service/add', methods=['POST'])
def admin_add_service():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    name = request.form.get('name'); duration = int(request.form.get('duration',30)); price = int(request.form.get('price',0))
    sv = Service(name=name,duration_minutes=duration,price=price)
    db.session.add(sv); db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/booking/delete/<int:bid>', methods=['POST'])
def admin_delete_booking(bid):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    b = Booking.query.get(bid)
    if b:
        db.session.delete(b); db.session.commit()
    return redirect(url_for('admin_dashboard'))

