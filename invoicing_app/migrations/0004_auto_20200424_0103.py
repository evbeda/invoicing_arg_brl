# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0003_auto_20200424_0059'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='changed',
            field=models.DateTimeField(db_index=True),
        ),
    ]
