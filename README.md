San Jose Barber - teljes csomag (mobil UI, admin jelszóval, email hook)

Telepítés (local):
1. python -m venv venv
2. source venv/bin/activate  (Windows: venv\Scripts\activate)
3. pip install -r requirements.txt
4. python main.py

Deploy Render:
- push to GitHub, then create Web Service on Render
- Build command: pip install -r requirements.txt
- Start command: gunicorn main:app
- In Render env vars set SMTP_USER, SMTP_PASS, ADMIN_EMAIL, SECRET_KEY (opcionális ADMIN_PASSWORD)
