from django.db import models
from datetime import timedelta


class Container(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')

    show_in_listing = models.BooleanField(default=True)
    vector = models.OneToOneField('fireplan.Vector', null=True, blank=True, on_delete=models.SET_NULL, related_name='container')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']



class Post(Container):
    def __str__(self):
        return f"Post: {self.name}"


class Vehicle(models.Model):
    identifier = models.CharField(max_length=50, primary_key=True)

    def __str__(self):
        return self.identifier


class RadioContainerLink(models.Model):
    name = models.CharField(max_length=100)
    radio = models.OneToOneField('radio.Radio', null=True, blank=True, on_delete=models.CASCADE, related_name="container_link")
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="radio_links")
    updated_at = models.DateTimeField(auto_now=True)
    temporary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    scan_interval = models.DurationField(default=timedelta(days=1))

    class Meta:
        unique_together = ('radio', 'container')
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.radio} in {self.container}'
