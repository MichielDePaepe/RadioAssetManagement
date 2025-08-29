from django.db import models
from radio.models import Radio

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]

    radio = models.ForeignKey(Radio, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    astrid_ticket = models.CharField(max_length=100, blank=True, null=True)
    siamu_ticket = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"#{self.id} - {self.title}"

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status_after = models.CharField(max_length=20, choices=Ticket.STATUS_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"Message for Ticket #{self.ticket.id} at {self.created_at}"