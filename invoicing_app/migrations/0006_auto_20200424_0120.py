# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0005_auto_20200424_0113'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentoptions',
            name='epp_address1',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='paymentoptions',
            name='epp_address2',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='paymentoptions',
            name='epp_city',
            field=models.CharField(default='', max_length=150),
        ),
        migrations.AddField(
            model_name='paymentoptions',
            name='epp_name_on_account',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='paymentoptions',
            name='epp_state',
            field=models.CharField(default='', max_length=30),
        ),
        migrations.AddField(
            model_name='paymentoptions',
            name='epp_zip',
            field=models.CharField(default='', max_length=10),
        ),
    ]
