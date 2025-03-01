import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import logging
from typing import Optional
from config import get_db, get_settings  # Import from config.py

# Configure logging (consider moving to a central location)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_email(recipient_email: str, subject: str, body: str, image_data: Optional[bytes] = None):
    """
    Sends an email.  Fetches configuration from the database.
    """
    db = get_db()
    settings = get_settings(db)

    sender_email = settings.get("sender_email")
    sender_password = settings.get("sender_password")
    smtp_server = settings.get("smtp_server") # Get from DB, no default here
    smtp_port = int(settings.get("smtp_port")) # Get from DB, no default here
    recipient_email = settings.get("recipient_email", recipient_email) # Get recipient email from settings, default to function argument if not found

    if not all([sender_email, sender_password, smtp_server, smtp_port, recipient_email]):
        logging.error("Email configuration is incomplete in the database.")
        return

    logging.info(f"Email Configuration: Sender={sender_email}, Server={smtp_server}:{smtp_port}, Recipient={recipient_email}")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject

    # Add body text
    message.attach(MIMEText(body, "plain"))

    # Add image attachment if provided
    if image_data:
        image = MIMEImage(image_data)
        message.attach(image)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        logging.info(f"Email sent successfully to {recipient_email}")

    except smtplib.SMTPAuthenticationError:
        logging.error("SMTP Authentication Error: Check your email credentials and ensure 'less secure apps' is enabled if using Gmail.")
    except Exception as e:
        logging.error(f"Error sending email: {e}") 