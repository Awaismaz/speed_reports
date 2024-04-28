from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=200, blank=True, null=True)
    
    # Additional fields
    company_header = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    site_code = models.CharField(max_length=100, blank=True, null=True)
    report_description = models.TextField(blank=True, null=True)
