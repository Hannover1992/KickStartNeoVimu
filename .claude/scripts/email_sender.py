#!/usr/bin/env python3
"""
Email-Versand Modul - Wiederverwendbar
Nutzt Gmail SMTP mit App Password.

Voraussetzung in ~/.bashrc:
  export GMAIL_ADDRESS="deine-email@gmail.com"
  export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
"""
import smtplib, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def send_email(subject, body, attachments=None, to=None):
    gmail_address = os.environ.get('GMAIL_ADDRESS')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
    if not gmail_address or not gmail_password:
        print("ERROR: GMAIL_ADDRESS / GMAIL_APP_PASSWORD nicht gesetzt")
        return False

    recipient = to or gmail_address
    msg = MIMEMultipart()
    msg['From'] = gmail_address
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html' if body.strip().startswith('<') else 'plain'))

    for filepath in (attachments or []):
        if not os.path.exists(filepath):
            print(f"WARNING: {filepath} nicht gefunden")
            continue
        with open(filepath, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                f'attachment; filename={os.path.basename(filepath)}')
            msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, recipient, msg.as_string())
        server.quit()
        print(f"Email gesendet an {recipient}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python email_sender.py <subject> <body> [--body-from-file <file>] [file1] [file2] ...")
        print("  --body-from-file <file>: Lies Body aus Datei (Inhalt wird Email-Body)")
        sys.exit(1)
    subject = sys.argv[1]
    body = sys.argv[2]
    attachments = sys.argv[3:] if len(sys.argv) > 3 else None
    if body == "--body-from-file" and len(sys.argv) > 3:
        with open(sys.argv[3], 'r', encoding='utf-8') as f:
            body = f.read()
        attachments = sys.argv[4:] if len(sys.argv) > 4 else None
    send_email(subject, body, attachments or None)
