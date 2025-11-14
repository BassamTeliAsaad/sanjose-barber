import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(BASE_DIR, 'data', 'bookings.db')
SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-me-to-a-secret'
SMTP_HOST = os.environ.get('SMTP_HOST') or 'smtp.gmail.com'
SMTP_PORT = int(os.environ.get('SMTP_PORT') or 587)
SMTP_USER = os.environ.get('SMTP_USER') or ''
SMTP_PASS = os.environ.get('SMTP_PASS') or ''
FROM_EMAIL = os.environ.get('FROM_EMAIL') or SMTP_USER
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or ''
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'barberadmin123'
GCAL_ENABLED = os.environ.get('GCAL_ENABLED') == '1'
