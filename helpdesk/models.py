# models.py
from django.db import models
from django.contrib.auth.models import User
from radio.models import *

class TicketType(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TicketStatus(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.code

        if self.default:
            TicketStatus.objects.exclude(pk=self.pk).update(default=False)
        elif not TicketStatus.objects.filter(default=True):
            self.default = True

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Ticket statuses"
        ordering = ['order']


def get_default_status():
    try:
        return TicketStatus.objects.get(default=True).pk
    except TicketStatus.DoesNotExist:
        return None



class Ticket(models.Model):
    class TicketPriority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    radio = models.ForeignKey("radio.Radio", on_delete=models.CASCADE, related_name="tickets")
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="tickets")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    status = models.ForeignKey(TicketStatus, on_delete=models.PROTECT, related_name="tickets", default=get_default_status)
    priority = models.CharField(max_length=10, choices=TicketPriority.choices, default=TicketPriority.MEDIUM)
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    siamu_ticket = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_tickets")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets")

    def __str__(self):
        return f"#{self.id} - {self.title}"


class TicketLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="logs")
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status_before = models.ForeignKey(TicketStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name="previous_logs")
    status_after = models.ForeignKey(TicketStatus, on_delete=models.SET_NULL, null=True, related_name="next_logs")
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Log {self.id} for Ticket #{self.ticket.id}"

    def save(self, *args, **kwargs):
        self.status_before = self.ticket.status
        self.ticket.status = self.status_after
        self.ticket.save()
        super().save(*args, **kwargs)

