# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentoptions',
            name='epp_tax_identifier',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
