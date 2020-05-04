# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Taken from AdbOrders.py
ORDER_STARTED = 1
ORDER_PENDING = 10
# Credit Card Processing
ORDER_PROCESSING = 15
ORDER_PROCESSED = 50
ORDER_UNPAID = 80
ORDER_PLACED = 100
ORDER_REFUNDED = 200
ORDER_TRANSFERRED = 220
# Deprecated
ORDER_DECLINED = 250
ORDER_ABANDONED = 300
ORDER_GATED = 350
ORDER_DELETED = 400

STATUS_CHOICES = (
    (ORDER_STARTED, 'Started'),
    (ORDER_PENDING, 'Pending'),
    (ORDER_PROCESSING, 'Processing'),
    (ORDER_UNPAID, 'Unpaid'),
    (ORDER_PLACED, 'Placed'),
    (ORDER_REFUNDED, 'Refunded'),
    (ORDER_TRANSFERRED, 'Transferred'),
    (ORDER_DECLINED, 'Declined'),
    (ORDER_ABANDONED, 'Abandoned'),
    (ORDER_GATED, 'Gated'),
    (ORDER_DELETED, 'Deleted'),
)

class SeriesEventModelMixin(object):

    @property
    def is_series(self):
        return bool(self.series and not self.is_repeating)

    @property
    def is_series_parent(self):
        return self.is_series and self.event_parent_id is None

class Order(models.Model):

    class Meta:
        managed = True
        db_table = 'Orders'

    status = models.IntegerField(
        choices=STATUS_CHOICES,
        db_index=True,
        default=ORDER_STARTED,
        null=True,
    )
    pp_date = models.DateTimeField(
        null=True,
    )
    changed = models.DateTimeField(
        db_index=True,
    )
    event = models.ForeignKey(
        'Event',
        db_column='event',
        db_index=True,
        on_delete=models.DO_NOTHING,
    )
    mg_fee = models.DecimalField(
        default=0,
        decimal_places=1,
        max_digits=5,
    )
    gross = models.DecimalField(
        default=0,
        decimal_places=1,
        max_digits=5,
    )
    eb_tax = models.DecimalField(
        default=0,
        decimal_places=1,
        max_digits=5,
    )


class PaymentOptions(models.Model):
    class Meta:
        managed = True
        db_table = 'Payment_Options'

    epp_country = models.CharField(
        max_length=50,
        default='',
    )
    accept_eventbrite = models.BooleanField(
        default=False,
    )
    event = models.OneToOneField(
        'Event',
        db_column='event',
        unique=True,
        db_index=True,
        # the related name is a bit hidden, we have a getter on the Event to
        # return None instead of raise DoesNotExist
        related_name='_paymentoptions',
        on_delete=models.DO_NOTHING,
    )
    epp_name_on_account = models.CharField(
        max_length=255,
        default='',
    )
    epp_address1 = models.CharField(
        max_length=255,
        default='',
    )
    epp_address2 = models.CharField(
        max_length=255,
        default='',
    )
    epp_zip = models.CharField(
        max_length=10,
        default='',
    )
    epp_city = models.CharField(
        max_length=150,
        default='',
    )
    epp_state = models.CharField(
        max_length=30,
        default='',
    )


class Event(
    models.Model,
    SeriesEventModelMixin
):

    class Meta:
        managed = True
        db_table = 'Events'

    event_name = models.CharField(
        db_column='name',
        max_length=20,
        default='',
    )

    series = models.NullBooleanField(
        default=False,
    )

    user = models.ForeignKey(
        'User',
        db_column='uid',
        db_index=True,
        null=True,
        on_delete=models.DO_NOTHING,
    )
    event_parent = models.ForeignKey(
        'Event',
        db_column='event_parent',
        related_name='children',
        db_index=True,
        null=True,
        on_delete=models.DO_NOTHING,
    )
    currency = models.CharField(
        default='USD',
        max_length=3,
    )
    repeat_schedule = models.NullCharField(
        max_length=40,
    )

    @property
    def is_repeating(self):
        return self.repeat_schedule != ''


class User(models.Model):
    username = models.CharField(max_length=50)
    ##Faltaria el meta, cuando probemos en QA adaptarlo segun nombre.

