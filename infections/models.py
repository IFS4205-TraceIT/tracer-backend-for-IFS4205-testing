import uuid
from django.db import models

class Closecontacts(models.Model):
    infected_user = models.ForeignKey('Users', on_delete=models.CASCADE, related_name="infected_user")
    contacted_user = models.ForeignKey('Users', on_delete=models.CASCADE, related_name="contacted_user")
    contact_timestamp = models.DateTimeField()
    rssi = models.DecimalField(max_digits=10, decimal_places=2)
    infectionhistory = models.ForeignKey('Infectionhistory', on_delete=models.CASCADE)

    class Meta:
        db_table = 'closecontacts'


class Contacttracers(models.Model):
    id = models.UUIDField(primary_key=True)

    class Meta:
        db_table = 'contacttracers'


class Infectionhistory(models.Model):
    user = models.ForeignKey('Users', on_delete=models.CASCADE)
    recorded_timestamp = models.DateTimeField()

    class Meta:
        db_table = 'infectionhistory'
        unique_together = (('user', 'recorded_timestamp'),)


class Notifications(models.Model):
    due_date = models.DateField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    tracer = models.ForeignKey(Contacttracers, on_delete=models.SET_NULL, blank=True, null=True)
    infection = models.OneToOneField(Infectionhistory, on_delete=models.CASCADE, primary_key = True)
    uploaded_status = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'notifications'


class Users(models.Model):
    id = models.UUIDField(primary_key=True)
    nric = models.TextField(unique=True)
    name = models.TextField()
    dob = models.DateField()
    email = models.TextField(blank=True)
    phone = models.TextField()
    gender = models.TextField()
    address = models.TextField()
    postal_code = models.TextField()

    class Meta:
        db_table = 'users'
