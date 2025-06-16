from django.db import models

class EmailTemplate(models.Model):
    subject = models.CharField(max_length=255)
    template_name = models.CharField(max_length=255, unique=True)  # e.g., 'welcome_email', 'otp_email'
    body = models.TextField()  # Store the body of the email (can be plain text or HTML)

    def __str__(self):
        return self.template_name