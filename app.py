from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
import config, smtplib
from email.message import EmailMessage

app = Flask(__name__)
app.config.from_object('config')
app.secret_key = app.config.get('SECRET_KEY') or 'change-this'

db = SQLAlchemy(app)

# Models
class Stylist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    work_days = db.Column(db.String(120), nullable=True)
    start_hour = db.Column(db.Integer, default=9)
    end_hour = db.Column(db.Integer, default=17)
    def to_dict(self):
        return {"id": self.id, "name": self.name, "work_days": self.work_days, "start_hour": self.start_hour, "end_hour": self.end_hour}

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=True)
    def to_dict(self):
        return {"id": self.id, "name": self.name, "duration_minutes": self.duration_minutes, "price": self.price}

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

# Ensure DB + seed
with app.app_context():
    db.create_all()
    if not Service.query.first():
        s1 = Stylist(name='Fodrász A', work_days='Mon,Tue,Wed,Thu,Fri', start_hour=9, end_hour=17)
        s2 = Stylist(name='Fodrász B', work_days='Sat', start_hour=10, end_hour=15)
        sv1 = Service(name='Hajvágás', duration_minutes=30, price=8000)
        sv2 = Service(name='Festés', duration_minutes=90, price=20000)
        sv3 = Service(name='Borotválás', duration_minutes=20, price=5000)
        db.session.add_all([s1, s2, sv1, sv2, sv3])
        db.session.commit()

# Helpers
def send_email(to_email, subject, body):
    if not app.config.get('SMTP_USER') or not app.config.get('SMTP_PASS'):
        app.logger.info('SMTP nincs beállítva — kihagyva az email küldés.')
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = app.config.get('FROM_EMAIL') or app.config.get('SMTP_USER')
        msg['To'] = to_email
        msg.set_content(body)
        # use TLS
        with smtplib.SMTP(app.config.get('SMTP_HOST'), app.config.get('SMTP_PORT')) as smtp:
            smtp.starttls()
            smtp.login(app.config.get('SMTP_USER'), app.config.get('SMTP_PASS'))
            smtp.send_message(msg)
        return True
    except Exception as e:
        app.logger.error('Email küldési hiba: %s', e)
        return False

# Routes
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
        return jsonify({'error':'hiányzó paraméter'}), 400
    try:
        stylist_id = int(stylist_id)
        date_obj = datetime.fromisoformat(date_str).date()
    except Exception:
        return jsonify({'error':'hibás dátum vagy fodrász'}), 400
    stylist = Stylist.query.get(stylist_id)
    if not stylist:
        return jsonify({'error':'Nincs ilyen fodrász.'}), 404
    service = Service.query.get(int(service_id)) if service_id else None
    duration = timedelta(minutes=service.duration_minutes) if service else timedelta(minutes=30)
    step = timedelta(minutes=15)
    current = datetime.combine(date_obj, time(hour=stylist.start_hour, minute=0))
    end_of_day = datetime.combine(date_obj, time(hour=stylist.end_hour, minute=0))
    bookings = Booking.query.filter(Booking.stylist_id==stylist_id,
                                     Booking.start_datetime >= current,
                                     Booking.start_datetime < end_of_day).all()
    def overlaps(a_start, a_end, b_start, b_end):
        return a_start < b_end and b_start < a_end
    slots = []
    while current + duration <= end_of_day:
        slot_free = True
        for b in bookings:
            if overlaps(current, current+duration, b.start_datetime, b.end_datetime):
                slot_free = False
                break
        slots.append({'start': current.isoformat(), 'free': slot_free})
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
        return jsonify({'error':'hibás dátum formátum'}), 400
    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error':'hibát találtunk a szolgáltatásban'}), 400
    end_dt = start_dt + timedelta(minutes=service.duration_minutes)
    booking = Booking(client_name=name, client_phone=phone, client_email=email,
                      stylist_id=stylist_id, service_id=service_id,
                      start_datetime=start_dt, end_datetime=end_dt)
    db.session.add(booking)
    db.session.commit()
    # send notifications
    admin_email = app.config.get('ADMIN_EMAIL')
    if email:
        send_email(email, 'San Jose Barber - Foglalás visszaigazolás', f'Kedves {name},\n\nSikeresen lefoglaltad: {start_dt} - {service.name}')
    if admin_email:
        send_email(admin_email, 'Új foglalás', f'Új foglalás: {name} - {service.name} - {start_dt} - Tel: {phone}')
    return jsonify({'ok': True})

# Admin: login and dashboard (password-protected via session)
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw and pw == app.config.get('ADMIN_PASSWORD'):
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Hibás jelszó.', 'error')
    return render_template('admin_login.html', title='Admin belépés')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    bookings = Booking.query.order_by(Booking.start_datetime.desc()).all()
    # enrich bookings with service/stylist names
    enriched = []
    for b in bookings:
        sv = Service.query.get(b.service_id)
        st = Stylist.query.get(b.stylist_id)
        enriched.append({'b': b, 'service_name': sv.name if sv else '', 'stylist_name': st.name if st else ''})
    return render_template('admin_dashboard.html', bookings=enriched, title='Admin - San Jose Barber')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/delete/<int:bid>', methods=['POST'])
def admin_delete(bid):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    b = Booking.query.get_or_404(bid)
    db.session.delete(b)
    db.session.commit()
    flash('Foglalás törölve.', 'success')
    return redirect(url_for('admin_dashboard'))

