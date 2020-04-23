# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event_name', models.CharField(max_length=50)),
                ('is_series_parent', models.BooleanField(default=False)),
                ('event_parent', models.ForeignKey(related_name='children', on_delete=django.db.models.deletion.DO_NOTHING, db_column='event_parent', to='invoicing_app.Event', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.IntegerField(default=1, null=True, db_index=True, choices=[(1, 'Started'), (10, 'Pending'), (15, 'Processing'), (80, 'Unpaid'), (100, 'Placed'), (200, 'Refunded'), (220, 'Transferred'), (250, 'Declined'), (300, 'Abandoned'), (350, 'Gated'), (400, 'Deleted')])),
                ('pp_date', models.DateTimeField(null=True)),
                ('changed', models.DateTimeField(auto_now=True, db_index=True)),
                ('mg_fee', models.DecimalField(default=0, max_digits=5, decimal_places=1)),
                ('gross', models.DecimalField(default=0, max_digits=5, decimal_places=1)),
                ('eb_tax', models.DecimalField(default=0, max_digits=5, decimal_places=1)),
                ('event', models.ForeignKey(db_column='event', on_delete=django.db.models.deletion.DO_NOTHING, to='invoicing_app.Event')),
            ],
        ),
        migrations.CreateModel(
            name='PaymentOptions',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('epp_country', models.CharField(max_length=50)),
                ('accept_eventbrite', models.BooleanField(default=False)),
                ('event', models.OneToOneField(related_name='_paymentoptions', on_delete=django.db.models.deletion.DO_NOTHING, db_column='event', to='invoicing_app.Event')),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=50)),
            ],
        ),
        migrations.AddField(
            model_name='event',
            name='user',
            field=models.ForeignKey(db_column='uid', on_delete=django.db.models.deletion.DO_NOTHING, to='invoicing_app.User', null=True),
        ),
    ]
