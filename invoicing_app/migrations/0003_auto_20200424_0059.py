# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0002_auto_20200424_0044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='changed',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
    ]
