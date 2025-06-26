from django.db import models

class Settings(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField(null=True, blank=True, editable=False)
