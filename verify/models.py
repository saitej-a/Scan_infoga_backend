from django.db import models

class AadharVerifyReport(models.Model):
    aadhaarNo = models.CharField(max_length=12, primary_key=True)
    result = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.aadhaarNo
    
