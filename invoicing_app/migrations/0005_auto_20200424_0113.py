# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0004_auto_20200424_0103'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='currency',
            field=models.CharField(default='USD', max_length=3),
        ),
        migrations.AlterField(
            model_name='event',
            name='event_name',
            field=models.CharField(max_length=20),
        ),
    ]
