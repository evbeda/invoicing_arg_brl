# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory


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
            'epp_state'
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
