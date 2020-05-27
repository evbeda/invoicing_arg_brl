# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory
import random
from datetime import datetime as dt


class TaxReceiptsFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.TaxReceipt'
        django_get_or_create = (
            'user_id',
            'event_id',
            'reporting_country_code',
            'currency',
            'status_id',
            'description',
            'base_amount',
            'total_taxable_amount',
            'tax_amount',
            'payment_transactions_count',
            'start_date_period',
            'end_date_period',
            'tax_regime_type_id',
            'recipient_type_id',
            'recipient_name',
            'recipient_address',
            'recipient_address_2',
            'recipient_postal_code',
            'recipient_city',
            'recipient_region',
            'recipient_tax_identifier_type_id',
            'recipient_tax_identifier_number',
            'recipient_tax_identifier_country_code',
            'supplier_type_id',
            'supplier_name',
            'supplier_address',
            'supplier_address_2',
            'supplier_postal_code',
            'supplier_city',
            'supplier_region',
            'supplier_tax_identifier_type_id',
            'supplier_tax_identifier_number',
            'supplier_tax_identifier_country_code',
        )
    user_id = ''
    event_id = ''
    reporting_country_code = random.choice(['AR', 'BR'])
    if reporting_country_code == 'AR':
        currency = 'ARS'
    else:
        currency = 'BRS'
    status_id = 2
    description = 'test_char_field'
    base_amount = 10
    total_taxable_amount = 10
    tax_amount = 10
    payment_transactions_count = 10
    start_date_period = str(dt(2020, 3, 1, 0, 0))
    end_date_period = str(dt(2020, 4, 1, 0, 0))
    if reporting_country_code == 'AR':
        tax_regime_type_id = random.choice([1, 2, 3, 4])
    else:
        tax_regime_type_id = None
    recipient_type_id = 2
    recipient_name = 'test_char_field'
    recipient_address = 'test_char_field'
    recipient_address_2 = 'test_char_field'
    recipient_postal_code = '6666'
    recipient_city = 'test_char_field'
    recipient_region = 'test_char_field'
    if reporting_country_code == 'AR':
        recipient_tax_identifier_type_id = 5
    else:
        recipient_tax_identifier_type_id = random.choice([3, 4])
    recipient_tax_identifier_number = '0123456789'
    recipient_tax_identifier_country_code = reporting_country_code
    supplier_type_id = 1
    supplier_name = 'Eventbrite'
    supplier_address = 'test_char_field'
    supplier_address_2 = 'test_char_field'
    supplier_postal_code = '5500'
    supplier_city = 'test_char_field'
    supplier_region = 'test_char_field'
    if reporting_country_code == 'AR':
        supplier_tax_identifier_type_id = 5
    else:
        supplier_tax_identifier_type_id = 3

    supplier_tax_identifier_number = '20123456789'
    supplier_tax_identifier_country_code = reporting_country_code
