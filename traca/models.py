from django.db import models

class Cabinet(models.Model):
    name = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
