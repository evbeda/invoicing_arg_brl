# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0006_auto_20200424_0120'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='event_name',
            field=models.CharField(default='', max_length=20),
        ),
        migrations.AlterField(
            model_name='paymentoptions',
            name='epp_country',
            field=models.CharField(default='', max_length=50),
        ),
    ]
