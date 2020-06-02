# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing_app', '0003_taxreceipt'),
    ]

    operations = [
        migrations.CreateModel(
            name='Users_Tax_Regimes',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tax_regime_type_id', models.CharField(max_length=20)),
                ('user_id', models.IntegerField(null=True, blank=True)),
            ],
            options={
                'db_table': 'Users_Tax_Regimes',
            },
        ),
    ]
