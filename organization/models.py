from django.db import models
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
