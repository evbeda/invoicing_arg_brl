# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from management.commands.generate_tax_receipts_old import Command
from datetime import datetime as dt
from mock import patch
from models import User, PaymentOptions, Event, Order

integration_result = (
    {
        'tax_receipt': {
            'supplier_city': u'Godoy Cruz',
            'supplier_address': u'Rep\xfablica del L\xedbano 981',
            'recipient_city': u'',
            'recipient_address_2': u'',
            'base_amount': {
                'currency': u'USD',
                'value': 110
            },
            'total_taxable_amount': {
                'currency': u'USD',
                'value': 400
            },
            'currency': u'USD',
            'recipient_type': 'ORGANIZER',
            'recipient_address': u'',
            'user_id': '1',
            'event_id': '1',
            'start_date_period': '2020-03-01 00:00:00-03:54',
            'recipient_postal_code': u'',
            'reporting_country_code': u'AR',
            'recipient_region': u'',
            'end_date_period': '2020-04-01 00:00:00-03:54',
            'tax_receipt_period_details': [{
                'end_date': '2020-04-01 00:00:00-03:54',
                'reference_type': 'ORDER',
                'base_amount': {
                    'currency': u'USD',
                    'value': 110
                },
                'taxable_amount': {
                    'currency': u'USD',
                    'value': 400
                },
                'tax_rate': 0,
                'start_date': '2020-03-01 00:00:00-03:54'
            }],
            'description': '',
            'supplier_region': u'Mendoza',
            'recipient_name': u'',
            'supplier_tax_information': {
                'tax_identifier_type': 'CUIT',
                'tax_identifier_country': u'AR',
                'tax_identifier_number': '30710388764'
            },
            'supplier_postal_code': u'5501',
            'supplier_name': u'Eventbrite Argentina S.A.',
            'supplier_type': 'EVENTBRITE',
            'supplier_address_2': '',
            'payment_transactions_count': 1
        }
    },
)


class TestScriptGenerateTaxHandle(TestCase):
    def setUp(self):
        self.options = {
            'user_id': None,
            'dry_run': False,
            'settings': None,
            'event_id': None,
            'pythonpath': None,
            'verbosity': 1,
            'traceback': False,
            'quiet': False,
            'today_date': '2020-04-08',
            'no_color': False,
            'country': 'AR',
            'logging': False
        }
        self.my_command = Command()

    def test_handle_periods(self):
        self.my_command.handle(**self.options)
        start = dt(2020, 03, 01, 00, 00, 00)
        end = dt(2020, 04, 01, 00, 00, 00)
        self.assertEqual(self.my_command.period_start, start)
        self.assertEqual(self.my_command.period_end, end)

    def test_handle_countries(self):
        self.my_command.handle(**self.options)
        self.assertEqual(
            self.my_command.declarable_tax_receipt_countries,
            ['AR']
        )

    def test_handle_with_no_country(self):
        options = {
            'user_id': None,
            'dry_run': False,
            'settings': None,
            'event_id': None,
            'pythonpath': None,
            'verbosity': 1,
            'traceback': False,
            'quiet': False,
            'today_date': '2020-04-08',
            'country': None,
            'no_color': False,
            'logging': False
        }
        self.my_command.handle(**options)
        self.assertEqual(
            self.my_command.declarable_tax_receipt_countries,
            ['AR', 'BR']
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.generate_tax_receipt_per_payment_options',
    )
    def test_select_declarable_orders(self, patch_generate):
        self.my_command.handle(**self.options)
        self.assertEqual(str(type(patch_generate.call_args[0][0])), "<type 'generator'>")

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.generate_tax_receipt_event'
    )
    def test_generate_tax_receipt_per_payment_options(self, patch_generate):
        my_user = User.objects.create(
            username='user_a',
        )
        my_event = Event.objects.create(
            event_name='event1',
            is_series_parent=False,
            user=my_user,
            event_parent=None,
        )
        my_pay_opt = PaymentOptions.objects.create(
            epp_country='AR',
            accept_eventbrite=False,
            event=my_event,
        )
        self.my_command.generate_tax_receipt_per_payment_options([my_pay_opt])
        self.assertEqual(
            str(type(patch_generate.call_args[0][0])),
            "<class 'invoicing_app.models.PaymentOptions'>"
        )
        self.assertEqual(
            str(type(patch_generate.call_args[0][1])),
            "<class 'invoicing_app.models.Event'>"
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.generate_tax_receipts'
    )
    def test_generate_tax_receipt_event(self, patch_generate):
        my_user = User.objects.create(
            username='user_a',
        )
        my_event = Event.objects.create(
            event_name='event1',
            is_series_parent=False,
            user=my_user,
            event_parent=None,
        )
        my_pay_opt = PaymentOptions.objects.create(
            epp_country='AR',
            accept_eventbrite=False,
            event=my_event,
        )
        my_order = Order.objects.create(
            status=100,
            pp_date=str(dt(2020, 3, 8, 0, 0)),
            changed=str(dt(2020, 3, 10, 0, 0)),
            event=my_event,
            mg_fee=5.1,
            gross=1.1,
            eb_tax=1.1,
        )
        self.my_command.dry_run = False
        self.my_command.period_start = dt(2020, 3, 1, 0, 0)
        self.my_command.period_end = dt(2020, 4, 1, 0, 0)
        self.my_command.generate_tax_receipt_event(my_pay_opt, my_event)

        self.assertEqual(
            str(type(patch_generate.call_args[0][0])),
            "<class 'invoicing_app.models.PaymentOptions'>"
        )
        self.assertEqual(
            str(type(patch_generate.call_args[0][1])),
            "<class 'invoicing_app.models.Event'>"
        )
        self.assertEqual(
            str(type(patch_generate.call_args[0][2])),
            "<type 'str'>"
        )
        self.assertEqual(
            str(type(patch_generate.call_args[0][3])),
            "<type 'str'>"
        )
        self.assertEqual(
            str(type(patch_generate.call_args[0][4])),
            "<type 'dict'>"
        )

    def test_localice_date(self):
        my_date = dt(2020, 4, 11, 0, 0)
        self.assertEqual(
            str(self.my_command.localice_date('AR', my_date)),
            "2020-04-11 00:00:00-03:54"
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service'
    )
    def test_generate_tax_receipts(self, patch_call):
        my_user = User.objects.create(
            username='AGUS_USER',
        )
        my_event = Event.objects.create(
            event_name='EVENT_1',
            is_series_parent=False,
            user=my_user,
            event_parent=None,
        )
        my_pay_opt = PaymentOptions.objects.create(
            epp_country='AR',
            accept_eventbrite=True,
            event=my_event,
        )
        my_order = Order.objects.create(
            status=100,
            pp_date=str(dt(2020, 3, 8, 0, 0)),
            changed=str(dt(2020, 3, 10, 0, 0)),
            event=my_event,
            mg_fee=5.1,
            gross=1.1,
            eb_tax=1.1,
        )
        self.my_command.handle(**self.options)
        self.assertEqual(
            patch_call.call_args[0],
            integration_result
        )
