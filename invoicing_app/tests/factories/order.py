# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory
from datetime import datetime as dt
from event import EventFactory


class OrderFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.Order'
        django_get_or_create = (
            'status',
            'pp_date',
            'changed',
            'event',
            'mg_fee',
            'gross',
            'eb_tax'
        )

    status = 100
    pp_date = str(dt(2020, 3, 8, 0, 0))
    changed = str(dt(2020, 3, 10, 0, 0))
    event = EventFactory.create()
    mg_fee = 5.1
    gross = 1.1
    eb_tax = 1.1
