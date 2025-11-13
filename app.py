from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///barber.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    duration_minutes = db.Column(db.Integer)
    price = db.Column(db.Integer)

    def to_dict(self):
        return dict(id=self.id,name=self.name,duration_minutes=self.duration_minutes,price=self.price)

class Stylist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    work_days = db.Column(db.String(200))
    start_hour = db.Column(db.Integer)
    end_hour = db.Column(db.Integer)

    def to_dict(self):
        return dict(id=self.id,name=self.name,work_days=self.work_days,start_hour=self.start_hour,end_hour=self.end_hour)

with app.app_context():
    db.create_all()
    if not Service.query.first():
        db.session.add_all([
            Service(name="Hajvágás", duration_minutes=30, price=8000),
            Service(name="Festés", duration_minutes=90, price=20000),
            Service(name="Borotválás", duration_minutes=20, price=5000)
        ])
        db.session.add_all([
            Stylist(name="Fodrász A", work_days="Mon,Tue,Wed,Thu,Fri", start_hour=9, end_hour=17),
            Stylist(name="Fodrász B", work_days="Sat", start_hour=10, end_hour=15)
        ])
        db.session.commit()

@app.route("/")
def index():
    services=[s.to_dict() for s in Service.query.all()]
    stylists=[s.to_dict() for s in Stylist.query.all()]
    return render_template("index.html", services=services, stylists=stylists, title="San Jose Barber")

@app.route("/api/book", methods=["POST"])
def book():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
