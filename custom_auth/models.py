from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import pyotp

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        
        # Generate OTP secret by default for all users
        user.otp_secret = pyotp.random_base32()
        
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(max_length=20, choices=[
        ('CORPORATE', 'Corporate'),
        ('DEVELOPER', 'Developer'),
        ('USER', 'User'),
        ('ADMIN', 'Admin')
    ], default='USER')
    date_joined = models.DateTimeField(auto_now_add=True, null=True)
    otp_secret = models.CharField(max_length=32)  # Remove blank=True, null=True to make it required

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

class CorporateProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='corporate_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company = models.CharField(max_length=200)
    domain = models.CharField(max_length=200)
    approval_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company} - {self.user.email}"

class DeveloperProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='developer_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    approval_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.user.email}"

class UserSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    ipAddress = models.GenericIPAddressField(null=True, blank=True) 
    device = models.CharField(max_length=200, default='Unknown')
    browser = models.CharField(max_length=200, default='Unknown')
    latitude = models.CharField(max_length=200, default='0')
    longitude = models.CharField(max_length=200, default='0')

    def __str__(self):
        return f"{self.email} - {self.sessionStartTime}"



class OTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return self.expires_at < timezone.now()

    def generate_otp(self):
        """Generate a new OTP, hash it, and set the expiration time to 10 minutes"""
        otp = pyotp.random_base32()[:6]  # Generate a 6-digit OTP
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()  # Hash OTP using SHA256
        self.otp_hash = otp_hash
        self.expires_at = timezone.now() + timedelta(minutes=10)  # OTP expires in 10 minutes
        self.save()
        return otp  # Return the plain OTP for email, but we store the hash


# 1: Scaninfoga Intelligence

class Bookmark(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_index=True)
    bookmark_page = models.IntegerField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
