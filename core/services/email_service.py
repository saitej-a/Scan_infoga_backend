# # core/services/email_service.py
# from django.core.mail import send_mail
# from django.conf import settings

# class EmailService:
#     @staticmethod
#     def send_email(subject, message, to_email, from_email=None):
#         """
#         Sends an email using the configured email backend in Django.
        
#         Args:
#             subject (str): The subject of the email.
#             message (str): The content of the email.
#             to_email (str): The recipient's email address.
#             from_email (str): The sender's email address (optional, uses DEFAULT_FROM_EMAIL if not provided).

#         Returns:
#             bool: True if the email was successfully sent, False otherwise.
#         """
#         from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
#         try:
#             send_mail(subject, message, from_email, [to_email])
#             return True  # Email sent successfully
#         except Exception as e:
#             # Log the exception (you can use logging here)
#             print(f"Failed to send email: {e}")
#             return False  # Email failed to send


# core/services/email_service.py
from django.core.mail import send_mail
from django.conf import settings
from core.models import EmailTemplate
# from core.utils.email_utils import get_email_template  # Import the utility to get email templates

class EmailService:
    @staticmethod
    def send_email(template_name, to_email, from_email=None, context=None):
        print("Inside mail service")
        """
        Sends an HTML email using the configured email backend in Django and loads email templates from the database.
        
        Args:
            template_name (str): The name of the email template (e.g., 'otp_email', 'welcome_email').
            to_email (str): The recipient's email address.
            from_email (str): The sender's email address (optional, uses DEFAULT_FROM_EMAIL if not provided).
            context (dict): A dictionary of variables to substitute in the email body (e.g., OTP or username).
        
        Returns:
            bool: True if the email was successfully sent, False otherwise.
        """
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
        # Load the template from the database
        try:
            subject, body = EmailTemplate.objects.get(template_name=template_name).subject, EmailTemplate.objects.get(template_name=template_name).body
            print("GOT OBJECT: ", subject, body)
        except ValueError:
            print("Value error")
            return False  # Template not found
        
        # Replace placeholders in the email body using the context (like OTP or username)
        if context:
            for key, value in context.items():
                body = body.replace(f"{{{{ {key} }}}}", str(value))  # Replace {key} with the actual value
        
        # Send the HTML email (with subject and body)
        try:
            send_mail(
                subject,           # Subject of the email
                body,              # Body of the email (plain text)
                from_email,        # From email address
                [to_email],        # To email address
                html_message=body  # HTML message (body of the email)
            )
            return True  # Email sent successfully
        except Exception as e:
            # Log the exception (you can use logging here)
            logger.error(f"Failed to send email: {e}")
            return False  # Email failed to send
