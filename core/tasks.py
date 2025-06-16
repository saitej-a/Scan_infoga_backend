from celery import shared_task
from core.services.email_service import EmailService

@shared_task
def send_welcome_email(user_email, name):
    context = {
        "username": name,
        # "site_url": "http://scaninfoga.com"
    }
    print("shared task")
    email_sent = EmailService.send_email(template_name="welcome_template", to_email=user_email, context=context)
    
    if email_sent:
        return "Welcome email sent successfully"
    else:
        return "Failed to send welcome email"

@shared_task
def send_otp_email(user_email, name, otp):
    context = {
        "username": name,
        "otp": otp,
    }
    print("shared task")
    email_sent = EmailService.send_email(template_name="otp_template", to_email=user_email, context=context)
    
    if email_sent:
        return "OTP email sent successfully"
    else:
        return "Failed to send OTP email"
        