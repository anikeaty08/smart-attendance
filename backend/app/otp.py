from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
from email.message import EmailMessage

from app.config import settings


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{otp}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_otp(otp: str, otp_hash: str | None) -> bool:
    if not otp_hash:
        return False
    try:
        salt, expected = otp_hash.split("$", 1)
    except ValueError:
        return False
    actual = hashlib.sha256(f"{salt}:{otp}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, expected)


def send_otp_email(email: str, otp: str) -> str:
    if not settings.smtp_host:
        print(f"[first-login-otp] {email}: {otp}")
        return "console"

    message = EmailMessage()
    message["Subject"] = "Smart Attendance first-login verification"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        f"Your Smart Attendance first-login OTP is {otp}.\n\n"
        f"It expires in {settings.first_login_otp_minutes} minutes. "
        "Do not share this code."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
    return "email"

