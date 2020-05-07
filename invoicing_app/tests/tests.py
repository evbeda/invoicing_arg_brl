# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from datetime import datetime as dt

from mock import patch

from django.core.management.base import CommandError

from invoicing_app.management.commands.generate_tax_receipts_old import Command as CommandOld
from invoicing_app.management.commands.generate_tax_receipts_new import Command as CommandNew

from factories.user import UserFactory
from factories.event import EventFactory
from factories.paymentoptions import PaymentOptionsFactory
from factories.order import OrderFactory


class TestScriptGenerateTaxReceiptsOldAndNew(TestCase):
    """
        Unittest for old and new scripts
    """
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
        }
        self.my_command = CommandOld()
        self.my_command_new = CommandNew()

    def test_handle_periods(self):
        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)
        start = dt(2020, 03, 01, 00, 00, 00)
        end = dt(2020, 04, 01, 00, 00, 00)
        self.assertEqual(self.my_command.period_start, start)
        self.assertEqual(self.my_command.period_end, end)
        self.assertEqual(self.my_command_new.period_start, start)
        self.assertEqual(self.my_command_new.period_end, end)

    def test_handle_countries(self):
        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)
        self.assertEqual(
            self.my_command.declarable_tax_receipt_countries,
            ['AR']
        )
        self.assertEqual(
            self.my_command_new.declarable_tax_receipt_countries,
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
            'use_po_dict': False,
        }
        self.my_command.handle(**options)
        self.my_command_new.handle(**options)
        self.assertEqual(
            self.my_command.declarable_tax_receipt_countries,
            ['AR', 'BR']
        )
        self.assertEqual(
            self.my_command_new.declarable_tax_receipt_countries,
            ['AR', 'BR']
        )

    def test_localize_date_old(self):
        my_date = dt(2020, 4, 11, 0, 0)
        self.assertEqual(
            str(self.my_command.localize_date('AR', my_date)),
            '2020-04-11 00:00:00-03:54'
        )
        self.assertEqual(
            str(self.my_command_new.localize_date('AR', my_date)),
            '2020-04-11 00:00:00-03:54'
        )

    def test_today_date_incorrect_format(self):
        # Not a string in correct format date
        self.options['today_date'] = 'a.asd-asd??++*asd'
        with self.assertRaises(CommandError) as cm:
            self.my_command.handle(**self.options)
        self.assertEqual(str(cm.exception), 'Date is not matching format YYYY-MM-DD')

        with self.assertRaises(CommandError):
            self.my_command_new.handle(**self.options)
        self.assertEqual(str(cm.exception), 'Date is not matching format YYYY-MM-DD')

    def test_invalid_country(self):
        self.options['country'] = 'ZZ'
        with self.assertRaises(CommandError) as cm:
            self.my_command.handle(**self.options)
        self.assertEqual(
            str(cm.exception),
            'The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)'
        )

        with self.assertRaises(CommandError) as cm:
            self.my_command_new.handle(**self.options)
        self.assertEqual(
            str(cm.exception),
            'The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)'
        )


class TestScriptGenerateTaxReceiptsOld(TestCase):
    """
        Unittest for the old script
    """
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
        }
        self.my_command = CommandOld()

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
        my_user = UserFactory.build()
        my_user.save()
        my_event = EventFactory.build(
            user=my_user
        )
        my_event.save()
        my_pay_opt = PaymentOptionsFactory.build(
            event=my_event
        )
        my_pay_opt.save()
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
        my_user = UserFactory.build()
        my_user.save()

        my_event = EventFactory.build(
            user=my_user
        )
        my_event.save()

        my_pay_opt = PaymentOptionsFactory.build(
            event=my_event,
        )
        my_pay_opt.save()

        my_order = OrderFactory.build(
            event=my_event,
        )
        my_order.save()
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
            "<type 'datetime.datetime'>"
        )
        self.assertEqual(
            str(type(patch_generate.call_args[0][3])),
            "<type 'datetime.datetime'>"
        )
        self.assertEqual(
            str(type(patch_generate.call_args[0][4])),
            "<type 'dict'>"
        )

    def test_quiet_option(self):
        self.options['quiet'] = True
        self.my_command.handle(**self.options)
        self.assertEqual(self.my_command.logger.name, 'null')

    def test_event_id_option(self):
        self.options['event_id'] = '1'
        self.my_command.handle(**self.options)
        self.assertEqual(
            self.my_command.event_id,
            self.options['event_id']
        )

    def test_id_user(self):
        self.options['user_id'] = '1'
        self.my_command.handle(**self.options)
        self.assertEqual(
            self.my_command.user_id,
            self.options['user_id']
        )


class TestIntegration(TestCase):
    """
        Integration tests for both scripts
    """
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
            'use_po_dict': False,
        }
        self.my_command = CommandOld()
        self.my_command_new = CommandNew()
        self.my_user = UserFactory.build()
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
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service'
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service'
    )
    def test_generate_tax_receipts(self, patch_call, patch_call_new):
        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)
        # Expected is 400 because mg_fee is 5.1 and eb_tax = 1.1
        expected_tot_tax_amount = 400
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )
        self.assertEqual(
            patch_call_new.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service'
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    def test_generate_tax_receipts_w_1_po_CL(self, patch_call, patch_call_new):
        my_user_2 = UserFactory.build()
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

        # Set the mg_fee in 11.0 to see that the element that goes to the service isn't this
        my_order_2 = OrderFactory.build(
            event=my_event_2,
            mg_fee=11.0
        )
        my_order_2.save()

        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)

        # Expected is 400 because mg_fee is 5.1 and eb_tax = 1.1
        expected_tot_tax_amount = 400
        call_once = 1

        self.assertEqual(
            patch_call.call_count,
            call_once
        )
        self.assertEqual(
            patch_call_new.call_count,
            call_once
        )
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )
        self.assertEqual(
            patch_call_new.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service',
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    def test_generate_tax_receipts_w_o_outdate(self, patch_call, patch_call_new):
        my_user_3 = UserFactory.build()
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
        self.my_command_new.handle(**self.options)
        # Expected is 400 because mg_fee is 5.1 and eb_tax = 1.1
        expected_tot_tax_amount = 400
        call_once = 1
        self.assertEqual(
            patch_call.call_count,
            call_once
        )
        self.assertEqual(
            patch_call_new.call_count,
            call_once
        )
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )
        self.assertEqual(
            patch_call_new.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service',
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    def test_generate_tax_receipts_w_2_calls(self, patch_call, patch_call_new):
        my_user_4 = UserFactory.build()
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
        self.my_command_new.handle(**self.options)
        # Expected is 400 because mg_fee is 11.0 and eb_tax = 1.1
        expected_tot_tax_amount = 990
        call_twice = 2
        self.assertEqual(
            patch_call.call_count,
            call_twice
        )
        self.assertEqual(
            patch_call_new.call_count,
            call_twice
        )
        self.assertEqual(
            patch_call.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )
        self.assertEqual(
            patch_call_new.call_args[0][0]['tax_receipt']['total_taxable_amount']['value'],
            expected_tot_tax_amount
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service',
    )
    def test_both_scripts(self, call_new, call_old):
        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)
        self.assertEqual(
            call_new.call_args[0][0],
            call_old.call_args[0][0]
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service',
    )
    def test_by_user(self, call_new, call_old):
        self.options['user_id'] = self.my_user.id

        my_user_7 = UserFactory.build()
        my_user_7.save()

        my_event_7 = EventFactory.build(
            user=my_user_7
        )
        my_event_7.save()

        my_pay_opt_7 = PaymentOptionsFactory.build(
            event=my_event_7,
        )
        my_pay_opt_7.save()

        my_order_7 = OrderFactory.build(
            event=my_event_7,
            mg_fee=11.0
        )
        my_order_7.save()

        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)

        call_once = 1

        self.assertEqual(
            call_new.call_count,
            call_once
        )
        self.assertEqual(
            call_old.call_count,
            call_once
        )
        self.assertEqual(
            call_new.call_args[0][0],
            call_old.call_args[0][0]
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service',
    )
    def test_by_event(self, call_new, call_old):
        self.options['event_id'] = self.my_event.id

        my_user_8 = UserFactory.build()
        my_user_8.save()

        my_event_8 = EventFactory.build(
            user=my_user_8
        )
        my_event_8.save()

        my_pay_opt_8 = PaymentOptionsFactory.build(
            event=my_event_8,
        )
        my_pay_opt_8.save()

        my_order_8 = OrderFactory.build(
            event=my_event_8,
            mg_fee=11.0
        )
        my_order_8.save()

        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)

        call_once = 1

        self.assertEqual(
            call_new.call_count,
            call_once
        )
        self.assertEqual(
            call_old.call_count,
            call_once
        )
        self.assertEqual(
            call_new.call_args[0][0],
            call_old.call_args[0][0]
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_old.Command.call_service',
    )
    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.call_service',
    )
    def test_childs(self, call_new, call_old):

        my_user_9 = UserFactory.build()
        my_user_9.save()
        my_event_9 = EventFactory.build(
            user=my_user_9,
        )
        my_event_9.series = True
        my_event_9.repeat_schedule = ''
        my_event_9.save()

        my_pay_opt_9 = PaymentOptionsFactory.build(
            event=my_event_9,
        )
        my_pay_opt_9.save()
        # ------------------------------------------------ #
        my_event_child_1 = EventFactory.build(
            user=my_user_9,
            event_parent=my_event_9
        )
        my_event_child_1.save()

        my_order_child_1 = OrderFactory.build(
            event=my_event_child_1
        )
        my_order_child_1.save()
        # ------------------------------------------------ #
        my_event_child_2 = EventFactory.build(
            user=my_user_9,
            event_parent=my_event_9
        )
        my_event_child_2.save()

        my_order_child_2 = OrderFactory.build(
            event=my_event_child_2
        )
        my_order_child_2.save()
        # ------------------------------------------------ #
        my_event_child_3 = EventFactory.build(
            user=my_user_9,
            event_parent=my_event_9
        )
        my_event_child_3.save()

        my_order_child_3 = OrderFactory.build(
            event=my_event_child_3
        )
        my_order_child_3.save()
        # ------------------------------------------------ #

        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)

        self.assertEqual(
            call_old.call_count,
            call_new.call_count
        )
