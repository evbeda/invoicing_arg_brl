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
                ('event', models.OneToOneField(related_name='_paymentoptions', on_delete=django.db.models.deletion.DO_NOTHING, db_column='event', to='invoicing_app.Event')),
            ],
            options={
                'db_table': 'Payment_Options',
                'managed': True,
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
