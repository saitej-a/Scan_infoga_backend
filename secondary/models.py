from django.db import models

class PayworldData(models.Model):
    sender_mobile_number = models.CharField(max_length=15, primary_key=True)
    result = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sender_mobile_number

class RazorpayIFSCData(models.Model):
    ifsc_code = models.CharField(max_length=11, primary_key=True)
    result = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.ifsc_code

