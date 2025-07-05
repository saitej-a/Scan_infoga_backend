import uuid
from django.db import models
from custom_auth.models import CustomUser as CustomUser

class WalletBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    # user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wallet')
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self.id)

class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    txn_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='transaction')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.CharField(max_length=100, null=True, blank=True)
    cf_response = models.JSONField(null=True, blank=True)
    credited_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return self.txn_id

class ApiPricing(models.Model):
    api_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.api_name

class SubscriptionHistory(models.Model):
    class SubscriptionPlans(models.TextChoices):
        FREE = 'FREE', 'Free'
        SILVER = 'SILVER', 'Silver'
        GOLD = 'GOLD', 'Gold'
        PLATINUM = 'PLATINUM', 'Platinum'
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='subscription_history')
    subscription_plan = models.CharField(max_length=10, choices=SubscriptionPlans.choices, default=SubscriptionPlans.FREE, db_index=True)
    txn_id=models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='subscription_history')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.api_name}"