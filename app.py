from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

db_path = os.path.join(os.path.dirname(__file__), "database.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)

class Stylist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(100), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"))
    stylist_id = db.Column(db.Integer, db.ForeignKey("stylist.id"))

with app.app_context():
    db.create_all()
    if Service.query.count() == 0:
        db.session.add_all([
            Service(name="Haircut", duration_minutes=30, price=25),
            Service(name="Beard Trim", duration_minutes=20, price=15),
            Service(name="Full Package", duration_minutes=50, price=35),
        ])
        db.session.commit()
    if Stylist.query.count() == 0:
        db.session.add_all([
            Stylist(name="John"),
            Stylist(name="Michael"),
            Stylist(name="David"),
        ])
        db.session.commit()

@app.route("/")
def index():
    services = Service.query.all()
    stylists = Stylist.query.all()
    services_data = [{"id":s.id,"name":s.name,"duration_minutes":s.duration_minutes,"price":s.price} for s in services]
    stylists_data = [{"id":s.id,"name":s.name} for s in stylists]
    return render_template("index.html", services=services_data, stylists=stylists_data, title="San Jose Barber")

@app.route("/book", methods=["POST"])
def book():
    data = request.json
    booking = Appointment(
        name=data["name"],
        phone=data["phone"],
        date=data["date"],
        time=data["time"],
        service_id=data["service_id"],
        stylist_id=data["stylist_id"],
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/appointments")
def appointments():
    all_appts = Appointment.query.all()
    response = [{"name":a.name,"phone":a.phone,"date":a.date,"time":a.time} for a in all_appts]
    return jsonify(response)
