# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0002_paymentoptions_epp_tax_identifier'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxReceipt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user_id', models.BigIntegerField()),
                ('event_id', models.BigIntegerField()),
                ('reporting_country_code', models.CharField(max_length=2, blank=True)),
                ('currency', models.CharField(max_length=3, blank=True)),
                ('status_id', models.IntegerField(null=True, blank=True)),
                ('description', models.CharField(max_length=255, blank=True)),
                ('base_amount', models.BigIntegerField(null=True, blank=True)),
                ('total_taxable_amount', models.BigIntegerField(null=True, blank=True)),
                ('tax_amount', models.BigIntegerField(null=True, blank=True)),
                ('payment_transactions_count', models.IntegerField(null=True, blank=True)),
                ('start_date_period', models.DateTimeField(null=True, blank=True)),
                ('end_date_period', models.DateTimeField(null=True, blank=True)),
                ('tax_regime_type_id', models.IntegerField(null=True, blank=True)),
                ('recipient_type_id', models.IntegerField(null=True, blank=True)),
                ('recipient_name', models.CharField(max_length=170, blank=True)),
                ('recipient_address', models.CharField(max_length=250, blank=True)),
                ('recipient_address_2', models.CharField(max_length=250, blank=True)),
                ('recipient_postal_code', models.CharField(max_length=12, blank=True)),
                ('recipient_city', models.CharField(max_length=50, blank=True)),
                ('recipient_region', models.CharField(max_length=50, blank=True)),
                ('recipient_tax_identifier_type_id', models.IntegerField(null=True, blank=True)),
                ('recipient_tax_identifier_number', models.CharField(max_length=255, null=True)),
                ('recipient_tax_identifier_country_code', models.CharField(max_length=2, blank=True)),
                ('supplier_type_id', models.IntegerField(null=True, blank=True)),
                ('supplier_name', models.CharField(max_length=170, blank=True)),
                ('supplier_address', models.CharField(max_length=250, blank=True)),
                ('supplier_address_2', models.CharField(max_length=250, blank=True)),
                ('supplier_postal_code', models.CharField(max_length=12, blank=True)),
                ('supplier_city', models.CharField(max_length=50, blank=True)),
                ('supplier_region', models.CharField(max_length=50, blank=True)),
                ('supplier_tax_identifier_type_id', models.IntegerField(null=True, blank=True)),
                ('supplier_tax_identifier_number', models.CharField(max_length=255, null=True)),
                ('supplier_tax_identifier_country_code', models.CharField(max_length=2, blank=True)),
            ],
            options={
                'db_table': 'Tax_Receipts',
            },
        ),
    ]
