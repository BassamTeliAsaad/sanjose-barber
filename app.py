from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
import smtplib
from email.message import EmailMessage
import config

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

class Stylist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    work_days = db.Column(db.String(120), nullable=True)
    start_hour = db.Column(db.Integer, default=9)
    end_hour = db.Column(db.Integer, default=17)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=True)

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

def send_email(to_email, subject, body):
    if not config.SMTP_USER or not config.SMTP_PASS:
        print('SMTP nincs beállítva - nem küldök emailt.')
        return
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = config.FROM_EMAIL or config.SMTP_USER
    msg['To'] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config.SMTP_USER, config.SMTP_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print('Email hiba:', e)

@app.route('/')
def index():
    services = Service.query.all()
    stylists = Stylist.query.all()
    return render_template('index.html', services=services, stylists=stylists, title='San Jose Barber')

@app.route('/api/availability')
def availability():
    try:
        stylist_id = int(request.args.get('stylist'))
        date_str = request.args.get('date')
        service_id = request.args.get('service')
    except Exception:
        return jsonify({'error':'Hibás paraméterek.'}), 400
    date_obj = datetime.fromisoformat(date_str).date()
    stylist = Stylist.query.get(stylist_id)
    if not stylist:
        return jsonify({'error':'Nincs ilyen fodrász.'}), 404
    if service_id:
        service = Service.query.get(int(service_id))
        duration = timedelta(minutes=service.duration_minutes)
    else:
        duration = timedelta(minutes=30)
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
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    stylist_id = int(data.get('stylist'))
    service_id = int(data.get('service'))
    start_iso = data.get('start')
    start_dt = datetime.fromisoformat(start_iso)
    service = Service.query.get(service_id)
    end_dt = start_dt + timedelta(minutes=service.duration_minutes)
    booking = Booking(client_name=name, client_phone=phone, client_email=email,
                      stylist_id=stylist_id, service_id=service_id,
                      start_datetime=start_dt, end_datetime=end_dt)
    db.session.add(booking)
    db.session.commit()
    try:
        if email:
            send_email(email, 'Foglalás visszaigazolás', f'Kedves {name},\\n\\nSikeresen lefoglaltad: {start_dt} - {service.name}')
        if config.ADMIN_EMAIL:
            send_email(config.ADMIN_EMAIL, 'Új foglalás', f'Új foglalás: {name} - {service.name} - {start_dt}')
    except Exception as e:
        print('Email hiba:', e)
    return jsonify({'ok': True})

@app.route('/admin')
def admin():
    stylists = Stylist.query.order_by(Stylist.name).all()
    services = Service.query.order_by(Service.name).all()
    bookings = Booking.query.order_by(Booking.start_datetime.desc()).all()
    return render_template('admin.html', stylists=stylists, services=services, bookings=bookings, title='Admin - San Jose Barber')

@app.route('/admin/stylist/add', methods=['POST'])
def add_stylist():
    name = request.form.get('name')
    start = int(request.form.get('start_hour', 9))
    end = int(request.form.get('end_hour', 17))
    days = request.form.get('work_days', 'Mon,Tue,Wed,Thu,Fri')
    s = Stylist(name=name, start_hour=start, end_hour=end, work_days=days)
    db.session.add(s)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/service/add', methods=['POST'])
def add_service():
    name = request.form.get('name')
    duration = int(request.form.get('duration', 30))
    price = int(request.form.get('price', 0))
    sv = Service(name=name, duration_minutes=duration, price=price)
    db.session.add(sv)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/booking/delete/<int:bid>', methods=['POST'])
def delete_booking(bid):
    b = Booking.query.get(bid)
    if b:
        db.session.delete(b)
        db.session.commit()
    return redirect(url_for('admin'))
