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

    epp_tax_identifier = models.CharField(
        null=True,
        max_length=255,
    )

    @property
    def epp_tax_identifier_type(self):
        if self.epp_country == 'BR':
            if len(self.epp_tax_identifier) > 11:
                return 'CNPJ'
            else:
                return 'CPF'
        if self.epp_country == 'AR':
            return 'CUIT'

        return ''


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

    repeat_schedule = models.CharField(
        max_length=40,
    )

    @property
    def is_repeating(self):
        return self.repeat_schedule != ''


class User(models.Model):
    class Meta:
        managed = True
        db_table = 'Users'

    first_name = models.CharField(max_length=50)


class TaxReceipt(models.Model):
    user_id = models.BigIntegerField()
    event_id = models.BigIntegerField()
    reporting_country_code = models.CharField(max_length=2, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    status_id = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    base_amount = models.BigIntegerField(null=True, blank=True)
    total_taxable_amount = models.BigIntegerField(null=True, blank=True)
    tax_amount = models.BigIntegerField(null=True, blank=True)
    payment_transactions_count = models.IntegerField(null=True, blank=True)
    start_date_period = models.DateTimeField(null=True, blank=True)
    end_date_period = models.DateTimeField(null=True, blank=True)
    tax_regime_type_id = models.IntegerField(null=True, blank=True)
    recipient_type_id = models.IntegerField(null=True, blank=True)
    recipient_name = models.CharField(max_length=170, blank=True)
    recipient_address = models.CharField(max_length=250, blank=True)
    recipient_address_2 = models.CharField(max_length=250, blank=True)
    recipient_postal_code = models.CharField(max_length=12, blank=True)
    recipient_city = models.CharField(max_length=50, blank=True)
    recipient_region = models.CharField(max_length=50, blank=True)
    recipient_tax_identifier_type_id = models.IntegerField(null=True, blank=True)
    recipient_tax_identifier_number = models.CharField(null=True, max_length=255)
    recipient_tax_identifier_country_code = models.CharField(max_length=2, blank=True)
    supplier_type_id = models.IntegerField(null=True, blank=True)
    supplier_name = models.CharField(max_length=170, blank=True)
    supplier_address = models.CharField(max_length=250, blank=True)
    supplier_address_2 = models.CharField(max_length=250, blank=True)
    supplier_postal_code = models.CharField(max_length=12, blank=True)
    supplier_city = models.CharField(max_length=50, blank=True)
    supplier_region = models.CharField(max_length=50, blank=True)
    supplier_tax_identifier_type_id = models.IntegerField(null=True, blank=True)
    supplier_tax_identifier_number = models.CharField(null=True, max_length=255)
    supplier_tax_identifier_country_code = models.CharField(max_length=2, blank=True)

    class Meta:
        db_table = "Tax_Receipts"


class Users_Tax_Regimes(models.Model):
    tax_regime_type_id = models.CharField(max_length=20)
    user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "Users_Tax_Regimes"