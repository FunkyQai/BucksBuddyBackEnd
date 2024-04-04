from django.db import models

class OpenAIFile(models.Model):
    file_id = models.CharField(max_length=200, unique=True)