from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
import config, os, smtplib, json, logging
from email.message import EmailMessage
app = Flask(__name__)

# ---- CONFIG ----
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "devsecret")

db = SQLAlchemy(app)

# ---- MODELS ----
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "duration": self.duration_minutes,
            "price": self.price
        }


class Stylist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    work_days = db.Column(db.String(200), nullable=False)   # "Mon,Tue,..."
    start_hour = db.Column(db.Integer, nullable=False)
    end_hour = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "work_days": self.work_days.split(","),
            "start_hour": self.start_hour,
            "end_hour": self.end_hour
        }


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(200))
    client_email = db.Column(db.String(200))
    stylist_id = db.Column(db.Integer, db.ForeignKey('stylist.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    start_time = db.Column(db.DateTime, nullable=False)

    stylist = db.relationship("Stylist")
    service = db.relationship("Service")


# ---- ROUTES ----

@app.route("/")
def index():
    services = Service.query.all()
    stylists = Stylist.query.all()
    return render_template("index.html",
                           services=[s.to_dict() for s in services],
                           stylists=[s.to_dict() for s in stylists],
                           title="San Jose Barber")


@app.route("/book", methods=["POST"])
def book():
    data = request.get_json()

    name = data["name"]
    email = data["email"]
    stylist_id = int(data["stylist"])
    service_id = int(data["service"])
    start_time = datetime.fromisoformat(data["start_time"])

    # check conflicts
    duration = Service.query.get(service_id).duration_minutes
    end_time = start_time + timedelta(minutes=duration)

    conflict = Booking.query.filter(
        Booking.stylist_id == stylist_id,
        Booking.start_time < end_time,
        (Booking.start_time + timedelta(minutes=duration)) > start_time
    ).first()

    if conflict:
        return jsonify({"error": "Időpont ütközés!"}), 400

    booking = Booking(
        client_name=name,
        client_email=email,
        stylist_id=stylist_id,
        service_id=service_id,
        start_time=start_time
    )
    db.session.add(booking)
    db.session.commit()

    return jsonify({"success": True})


@app.route("/admin")
def admin_panel():
    bookings = Booking.query.order_by(Booking.start_time.asc()).all()
    return render_template("admin.html", bookings=bookings)


@app.route("/admin/delete/<int:id>")
def delete(id):
    b = Booking.query.get(id)
    db.session.delete(b)
    db.session.commit()
    return redirect("/admin")


# ---- CREATE TABLES (FLASK 3 FIX) ----
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run()
