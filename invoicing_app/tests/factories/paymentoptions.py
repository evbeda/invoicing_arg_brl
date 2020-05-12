# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory
import random
import string


class PaymentOptionsFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.PaymentOptions'
        django_get_or_create = (
            'epp_country',
            'accept_eventbrite',
            'event',
            'epp_name_on_account',
            'epp_address1',
            'epp_address2',
            'epp_zip',
            'epp_city',
            'epp_state',
            'epp_tax_identifier',
        )

    epp_country = 'AR'
    accept_eventbrite = True
    event = None
    epp_name_on_account = ''
    epp_address1 = ''
    epp_address2 = ''
    epp_zip = ''
    epp_city = ''
    epp_state = ''
    epp_tax_identifier = ''.join(random.choice(string.lowercase) for x in range(random.randint(11, 12)))
