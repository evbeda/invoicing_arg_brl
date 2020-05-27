# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import invoicing_app.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event_name', models.CharField(default='', max_length=20, db_column='name')),
                ('series', models.NullBooleanField(default=False)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('repeat_schedule', models.CharField(max_length=40)),
                ('event_parent', models.ForeignKey(related_name='children', on_delete=django.db.models.deletion.DO_NOTHING, db_column='event_parent', to='invoicing_app.Event', null=True)),
            ],
            options={
                'db_table': 'Events',
                'managed': True,
            },
            bases=(models.Model, invoicing_app.models.SeriesEventModelMixin),
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.IntegerField(default=1, null=True, db_index=True, choices=[(1, 'Started'), (10, 'Pending'), (15, 'Processing'), (80, 'Unpaid'), (100, 'Placed'), (200, 'Refunded'), (220, 'Transferred'), (250, 'Declined'), (300, 'Abandoned'), (350, 'Gated'), (400, 'Deleted')])),
                ('pp_date', models.DateTimeField(null=True)),
                ('changed', models.DateTimeField(db_index=True)),
                ('mg_fee', models.DecimalField(default=0, max_digits=5, decimal_places=1)),
                ('gross', models.DecimalField(default=0, max_digits=5, decimal_places=1)),
                ('eb_tax', models.DecimalField(default=0, max_digits=5, decimal_places=1)),
                ('event', models.ForeignKey(db_column='event', on_delete=django.db.models.deletion.DO_NOTHING, to='invoicing_app.Event')),
            ],
            options={
                'db_table': 'Orders',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='PaymentOptions',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('epp_country', models.CharField(default='', max_length=50)),
                ('accept_eventbrite', models.BooleanField(default=False)),
                ('epp_name_on_account', models.CharField(default='', max_length=255)),
                ('epp_address1', models.CharField(default='', max_length=255)),
                ('epp_address2', models.CharField(default='', max_length=255)),
                ('epp_zip', models.CharField(default='', max_length=10)),
                ('epp_city', models.CharField(default='', max_length=150)),
                ('epp_state', models.CharField(default='', max_length=30)),
                ('epp_tax_identifier', models.CharField(max_length=255, null=True)),
                ('event', models.OneToOneField(related_name='_paymentoptions', on_delete=django.db.models.deletion.DO_NOTHING, db_column='event', to='invoicing_app.Event')),
            ],
            options={
                'db_table': 'Payment_Options',
                'managed': True,
            },
        ),
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
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'Users',
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='event',
            name='user',
            field=models.ForeignKey(db_column='uid', on_delete=django.db.models.deletion.DO_NOTHING, to='invoicing_app.User', null=True),
        ),
    ]
