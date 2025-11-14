San Jose Barber - Full feature package

Includes:
- Mobile-first app-style UI
- Calendar-based slot selection
- Admin with password protection (env var ADMIN_PASSWORD)
- Email notifications (configure SMTP_USER and SMTP_PASS)
- Conflict checking on booking
- Dark / Light toggle (client-side)
- Google Calendar integration: placeholder hook (GCAL_ENABLED env var)
- Compatible with Render (use gunicorn main:app)

Quick local run:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
