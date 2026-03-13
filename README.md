# Job Board (Recruiters + Job Seekers) - Django

## Setup (first time)

1. Clone the repo
2. Install Django (5.0)

3. Run migrations
   python manage.py migrate

4. Create an admin user
   python manage.py createsuperuser

5. Start the server
   python manage.py runserver

## Local Email Setup

The project uses environment variables for SMTP email. Each developer who wants real email sending locally must set these in the same terminal session before running the server:

```bash
export EMAIL_HOST_USER="mintmatch6@gmail.com"
export EMAIL_HOST_PASSWORD="your_google_app_password"
export DEFAULT_FROM_EMAIL="mintmatch6@gmail.com"
```

Then start Django normally:

```bash
python3 manage.py runserver
```

To verify email is working:

```bash
python3 manage.py shell
```

```python
from django.core.mail import send_mail
send_mail("MintMatch Email Test", "If you received this, SMTP is working.", None, ["your_email@example.com"], fail_silently=False)
```

If `send_mail(...)` returns `1`, the email was successfully handed to the SMTP backend.

## Admin Panel

- Visit: http://127.0.0.1:8000/admin/

## Notes

- Local database (db.sqlite3) is not committed to the repo.
- Each developer runs migrations and creates their own superuser locally.
- Developed initially in Python 3.13.5
- Email credentials are not stored in the repo. Do not commit app passwords or hardcode them in `config/settings.py`.
