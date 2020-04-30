# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from invoicing_app.models import User, PaymentOptions, Event, Order
from datetime import datetime as dt

from mock import patch

from invoicing_app.management.commands.generate_tax_receipts_old import Command as CommandOld
from invoicing_app.management.commands.generate_tax_receipts_new import Command as CommandNew

from factories.user import UserFactory
from factories.event import EventFactory
from factories.paymentoptions import PaymentOptionsFactory
from factories.order import OrderFactory


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
            'logging': False,
            'test': False,
        }
        self.my_command = CommandOld()

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
            'logging': False,
            'test': False,
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


class TestIntegration(TestCase):

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
            'logging': False,
            'test': False,
        }
        self.my_command = CommandOld()
        self.my_user = UserFactory.build(username='user_1')
        self.my_user.save()

        self.my_event = EventFactory.build(
            user=self.my_user
        )
        self.my_event.save()

        self.my_pay_opt = PaymentOptionsFactory.build(
            event=self.my_event,
        )
        self.my_pay_opt.save()

        self.my_order = OrderFactory.build(
            event=self.my_event,
        )
        self.my_order.save()

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service'
    )
    def test_generate_tax_receipts(self, patch_call):
        self.my_command.handle(**self.options)
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            400
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    def test_generate_tax_receipts_w_1_po_CL(self, patch_call):
        my_user_2 = UserFactory.build(
            username='user_2'
        )
        my_user_2.save()

        my_event_2 = EventFactory.build(
            user=my_user_2
        )
        my_event_2.save()

        my_pay_opt_2 = PaymentOptionsFactory.build(
            event=my_event_2,
            epp_country='CL'
        )
        my_pay_opt_2.save()

        # Set the mg_fsee in 11.0 to see that the element that goes to the service isn't this
        my_order_2 = OrderFactory.build(
            event=my_event_2,
            mg_fee=11.0
        )
        my_order_2.save()

        self.my_command.handle(**self.options)
        self.assertEqual(
            patch_call.call_count,
            1
        )
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            400
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    def test_generate_tax_receipts_w_o_oudate(self, patch_call):
        my_user_3 = UserFactory.build(
            username='user_2'
        )
        my_user_3.save()

        my_event_3 = EventFactory.build(
            user=my_user_3
        )
        my_event_3.save()

        my_pay_opt_3 = PaymentOptionsFactory.build(
            event=my_event_3,
        )
        my_pay_opt_3.save()

        # Set the mg_fee in 11.0 to see that the element that goes to the service isn't this
        my_order_3 = OrderFactory.build(
            event=my_event_3,
            mg_fee=11.0,
            pp_date=str(dt(2020, 07, 10, 0, 0))
        )
        my_order_3.save()

        self.my_command.handle(**self.options)
        self.assertEqual(
            patch_call.call_count,
            1
        )
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            400
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    def test_generate_tax_receipts_w_2_calls(self, patch_call):
        my_user_4 = UserFactory.build(
            username='user_2'
        )
        my_user_4.save()

        my_event_4 = EventFactory.build(
            user=my_user_4
        )
        my_event_4.save()

        my_pay_opt_4 = PaymentOptionsFactory.build(
            event=my_event_4,
        )
        my_pay_opt_4.save()

        # Set the mg_fee in 11.0 to see that the element that goes to the service is this
        my_order_4 = OrderFactory.build(
            event=my_event_4,
            mg_fee=11.0,
        )
        my_order_4.save()

        self.my_command.handle(**self.options)
        self.assertEqual(
            patch_call.call_count,
            2
        )
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            990
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    def test_generate_tax_with_child(self, patch_call):
        my_user_5 = UserFactory.build(
            username='user_2'
        )
        my_user_5.save()

        my_event_5 = EventFactory.build(
            user=my_user_5,
            is_series_parent=True
        )
        my_event_5.save()

        my_pay_opt_5 = PaymentOptionsFactory.build(
            event=my_event_5
        )
        my_pay_opt_5.save()

        # Set the mg_fee in 11.0 to see that the element that goes to the service isn't this
        my_order_5 = OrderFactory.build(
            event=my_event_5,
            mg_fee=11.0,
        )
        my_order_5.save()

        my_user_6 = UserFactory.build(
            username='user_3'
        )
        my_user_6.save()

        my_event_6 = EventFactory.build(
            user=my_user_6,
            event_parent=my_event_5
        )
        my_event_6.save()

        my_pay_opt_6 = my_pay_opt_5
        my_pay_opt_6.save()
        # Set the mg_fee in 14.0 to see that the element that goes to the service is this
        my_order_6 = OrderFactory.build(
            event=my_event_6,
            mg_fee=14.0,
        )
        my_order_6.save()

        self.my_command.handle(**self.options)
        self.assertEqual(
            patch_call.call_count,
            2
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service',
    )
    def test_booth_scripts(self, call_new, call_old):
        my_command_new = CommandNew()
        self.my_command.handle(**self.options)
        my_command_new.handle(**self.options)
        self.assertEqual(
            call_new.call_args[0][0],
            call_old.call_args[0][0]
        )
