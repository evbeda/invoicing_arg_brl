# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from datetime import datetime as dt
from time import sleep
import random
import string
from mock import patch

from django.core.management.base import CommandError

from invoicing_app.management.commands.generate_tax_receipts_old import Command as CommandOld
from invoicing_app.management.commands.generate_tax_receipts_new import Command as CommandNew
from invoicing_app.management.commands.update_incomplete_tax_receipts import Command as UpdateIncompleteCommand

from factories.user import UserFactory
from factories.event import EventFactory
from factories.paymentoptions import PaymentOptionsFactory
from factories.order import OrderFactory
from factories.tax_receipts import TaxReceiptsFactory
from factories.users_tax_regimes import UserTaxRegimesFactory
from invoicing_app.circuitbreaker import CircuitBreaker

from invoicing_app.tax_receipt_generator import (
    CountryNotConfiguredException,
    IncorrectFormatDateException,
    NoCountryProvidedException,
    TaxReceiptGenerator,
    TaxReceiptGeneratorRequest,
    UserAndEventProvidedException
)

from decimal import Decimal

from django.core.management import call_command

from invoicing_app.slack_module import SlackConnection
from invoicing_app.mail_report_module import GenerationProccessMailReport

path_tax_receipt_generator = 'invoicing_app.tax_receipt_generator.TaxReceiptGenerator.'
generate_script_name = 'generate_entry_point'


class TestScriptGenerateTaxReceiptsOldAndNew(TestCase):
    """
        Unittest for old and new scripts
    """

    def setUp(self):
        self.options = {
            'user_id': None,
            'dry_run': True,
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
            'AR'
        )
        self.assertNotIn(
            'CONDITION_MASK',
            self.my_command_new.query
        )

    def test_handle_with_no_country(self):
        options = {
            'user_id': None,
            'dry_run': True,
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
        self.assertEqual(
            self.my_command.declarable_tax_receipt_countries,
            ['AR', 'BR']
        )
        with self.assertRaises(CommandError) as cm:
            self.my_command_new.handle(**options)
        self.assertEqual(
            str(cm.exception),
            'No country provided. It provides: command --country="EX" (AR-Argentina or BR-Brazil)'
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

    def test_event_id_option(self):
        self.options['event_id'] = '1'

        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)

        self.assertEqual(
            self.my_command.event_id,
            self.options['event_id']
        )
        self.assertEqual(
            self.my_command_new.event_id,
            self.options['event_id']
        )

    def test_user_id_option(self):
        self.options['user_id'] = '1'

        self.my_command.handle(**self.options)
        self.my_command_new.handle(**self.options)

        self.assertEqual(
            self.my_command.user_id,
            self.options['user_id']
        )
        self.assertEqual(
            self.my_command_new.user_id,
            self.options['user_id']
        )


class TestScriptGenerateTaxReceiptsOld(TestCase):
    """
        Unittest for the old script
    """

    def setUp(self):
        self.options = {
            'user_id': None,
            'dry_run': True,
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
        self.my_command.dry_run = True
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


class TestScriptGenerateTaxReceiptsNew(TestCase):
    """
        Unittest for the new script
    """

    def setUp(self):
        self.options = {
            'user_id': None,
            'dry_run': True,
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

    def test_pass_envet_and_user_options(self):
        self.options['user_id'] = 1
        self.options['event_id'] = 1

        with self.assertRaises(CommandError) as cm:
            self.my_command_new.handle(**self.options)
        self.assertEqual(
            str(cm.exception),
            'Can not use both options in the same time'
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.iterate_querys_results'
    )
    def test_get_and_iterate_no_series_events(self, patch_iterate):
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': self.options['country'],
            'status_query': 100,
        }
        self.my_command_new.query = self.my_command_new.query.replace(
            '{condition_mask}',
            ''
        )
        self.my_command_new.get_and_iterate_no_series_events(query_options_test)
        returns_one_element = 1
        self.assertEqual(
            len(patch_iterate.call_args[0][0]),
            returns_one_element
        )
        self.assertEqual(
            patch_iterate.call_args[0][1],
            query_options_test['localize_start_date_query']
        )
        self.assertEqual(
            patch_iterate.call_args[0][2],
            query_options_test['localize_end_date_query']
        )

    @patch(
        'invoicing_app.management.commands.generate_tax_receipts_new.Command.iterate_querys_results'
    )
    def test_get_and_iterate_child_events(self, patch_iterate):
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': self.options['country'],
            'status_query': 100,
        }
        self.my_command_new.query = self.my_command_new.query.replace(
            '{condition_mask}',
            ''
        )
        self.my_command_new.get_and_iterate_child_events(query_options_test)
        returns_zero_elements = 0
        self.assertEqual(
            len(patch_iterate.call_args[0][0]),
            returns_zero_elements
        )
        self.assertEqual(
            patch_iterate.call_args[0][1],
            query_options_test['localize_start_date_query']
        )
        self.assertEqual(
            patch_iterate.call_args[0][2],
            query_options_test['localize_end_date_query']
        )

    def test_get_query_results(self):
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': self.options['country'],
            'status_query': 100,
        }
        self.my_command_new.query = self.my_command_new.query.replace(
            '{condition_mask}',
            ''
        )
        self.my_command_new.query = self.my_command_new.query.replace(
            '{parent_child_mask}',
            '(`Events`.`id` = `Payment_Options`.`event`)'
        )
        returns_one_element = 1
        self.assertIsInstance(
            self.my_command_new.get_query_results(
                query_options_test, self.my_command_new.query
            ),
            list
        )
        self.assertEqual(
            len(self.my_command_new.get_query_results(
                query_options_test, self.my_command_new.query
            )),
            returns_one_element
        )


class TestIntegration(TestCase):
    """
        Integration tests for both scripts
    """

    def setUp(self):
        self.options = {
            'user_id': None,
            'dry_run': True,
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


class TestCircuitBreaker(TestCase):
    def setUp(self):
        def division(a, b):
            try:
                return a // b
            except Exception as e:
                raise e

        self.circuit_breaker = CircuitBreaker(
            threshold=3,
            timeout=1,
            exception=ZeroDivisionError,
            external_service=division
        )

    def test_service_ok(self):
        call = self.circuit_breaker.call_external_service(2, 2)
        self.assertEquals(self.circuit_breaker.show_state, "CLOSED")
        self.assertEquals(call, 1)

    def test_threshold_reached_and_circuit_opens(self):
        # Most tests use 2 0 as *args to test faulty services because 2 / 0 raises an Exception
        self.circuit_breaker.call_external_service(2, 0)
        self.circuit_breaker.call_external_service(2, 0)
        self.circuit_breaker.call_external_service(2, 0)
        self.circuit_breaker.call_external_service(2, 0)
        self.assertEqual(self.circuit_breaker.show_state, "OPEN")

    def test_half_open_state_reached(self):
        self.circuit_breaker.call_external_service(2, 0)
        self.circuit_breaker.call_external_service(2, 0)
        self.circuit_breaker.call_external_service(2, 0)
        # Sleep time to update circuit state to HALF OPEN
        sleep(2)
        self.circuit_breaker.call_external_service(2, 0)
        self.assertEquals(self.circuit_breaker.show_state, "HALF-OPEN")

    def test_string_info_from_circuit_breaker(self):
        expected_str = '''
        Circuit Breaker info:
        -Function registered: Division,
        -Time since last failure: 0s,
        -Circuit state: CLOSED,
        -Circuit timeout: 1s,
        -Circuit threshold: 3,
        -Expected exception: ZeroDivisionError
        '''
        self.assertEquals(str(self.circuit_breaker), expected_str)


class TestUpdateTaxReceipts(TestCase):
    def setUp(self):
        self.command = UpdateIncompleteCommand()
        self.options = {
            'verbose': False,
            'dry_run': False,
        }

        self.user = UserFactory.create()
        self.event = EventFactory.create(
            user=self.user,
        )

        self.tax_receipt = TaxReceiptsFactory.create(
            event_id=self.event.id,
            user_id=self.user.id,
            status_id=1
        )

        self.payment_options = PaymentOptionsFactory.create(
            event=self.event,
        )
        self.user_tax_regime = UserTaxRegimesFactory.create(
            user_id=self.tax_receipt.user_id,
            tax_regime_type_id=1,
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._log_due_to_missing_to_info',
    )
    def test_check_BR_requirements_zip_cpf_error(self, log_due_to_missing_to_info):
        country = 'BR'
        self.command.verbose = True

        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.recipient_postal_code = ''
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.epp_address1 = 'address1'
        self.payment_options.epp_zip = '2132'
        self.payment_options.epp_city = 'city'
        self.payment_options.epp_state = 'state'
        self.payment_options.epp_tax_identifier = ''.join(random.choice(string.lowercase) for _ in range(11))

        self.payment_options.save()

        self.command._check_BR_requirements(self.tax_receipt, self.payment_options)

        self.assertEqual(
            log_due_to_missing_to_info.call_args[0][0],
            self.tax_receipt.id
        )

        self.assertEqual(
            log_due_to_missing_to_info.call_args[0][1],
            self.payment_options.id
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._log_due_to_missing_to_info',
    )
    def test_check_BR_requirements_zip_cnpj_error(self, log_due_to_missing_to_info):
        country = 'BR'
        self.command.verbose = True

        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.recipient_postal_code = ''
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.epp_name_on_account = 'epp_name_on_account'
        self.payment_options.epp_zip = '2132'
        self.payment_options.epp_city = 'city'
        self.payment_options.epp_state = 'state'
        self.payment_options.epp_tax_identifier = ''.join(random.choice(string.lowercase) for _ in range(12))

        self.payment_options.save()

        self.command._check_BR_requirements(self.tax_receipt, self.payment_options)

        self.assertEqual(
            log_due_to_missing_to_info.call_args[0][0],
            self.tax_receipt.id
        )

        self.assertEqual(
            log_due_to_missing_to_info.call_args[0][1],
            self.payment_options.id
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._log_hosts_being_used',
    )
    def test_update_incomplete_tax_receipt_handle_dry_run(self, log_hosts_being_used):
        country = 'BR'
        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.epp_address1 = 'address1'
        self.payment_options.epp_name_on_account = 'epp_name_on_account'
        self.payment_options.epp_zip = '2132'
        self.payment_options.epp_city = 'city'
        self.payment_options.epp_state = 'state'
        self.payment_options.epp_tax_identifier = ''.join(random.choice(string.lowercase) for _ in range(11))
        self.payment_options.save()

        self.command.billing = 'default'
        self.command.handle(**self.options)

        self.assertEqual(
            self.command.count,
            1
        )


class TestTaxReceiptGeneratorRequest(TestCase):

    @patch.object(
        TaxReceiptGeneratorRequest, '_post_validate'
    )
    @patch.object(
        TaxReceiptGeneratorRequest, '_validate'
    )
    def test_init(self, patch_validate, patch_post):
        # Here doesn't raise the user-event exception 'cause the validate and post_validate aren't executed
        my_request = TaxReceiptGeneratorRequest(
            country='AR',
            user_id=123,
            event_id=456,
            today_date='2020-05-11'
        )
        self.assertTrue(patch_validate.called)
        self.assertTrue(patch_post.called)

        self.assertEqual(my_request.country, 'AR')
        self.assertEqual(my_request.user_id, 123)
        self.assertEqual(my_request.event_id, 456)
        self.assertEqual(my_request.today_date, '2020-05-11')

    @patch.object(
        TaxReceiptGeneratorRequest, '_post_validate'
    )
    def test_validate_country(self, patch_post):
        with self.assertRaises(CountryNotConfiguredException) as e:
            my_request = TaxReceiptGeneratorRequest(country='CL', today_date=None, user_id=None, event_id=None)
            self.assertEqual(
                e.message,
                'The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)'
            )

    @patch.object(
        TaxReceiptGeneratorRequest, '_post_validate'
    )
    def test_validate_no_country(self, patch_post):
        with self.assertRaises(NoCountryProvidedException) as e:
            my_request = TaxReceiptGeneratorRequest(country=None, today_date=None, user_id=None, event_id=None)
            self.assertEqual(
                e.message,
                'No country provided. It provides: command --country="EX" (AR-Argentina or BR-Brazil)'
            )

    @patch.object(
        TaxReceiptGeneratorRequest, '_post_validate'
    )
    def test_validate_user_and_event(self, patch_validate):
        with self.assertRaises(UserAndEventProvidedException) as e:
            my_request = TaxReceiptGeneratorRequest(country='AR', today_date=None, user_id=1, event_id=1)
            self.assertEqual(
                e.message,
                'Can not use event and user options in the same time'
            )

    @patch.object(
        TaxReceiptGeneratorRequest, '_post_validate'
    )
    def test_validate_today_date(self, patch_post):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date='2020-05-11', user_id=None, event_id=None)
        expected_today = dt(2020, 5, 11, 0, 0)
        expected_end_date = dt(2020, 5, 11, 0, 0)
        self.assertEqual(my_request.today, expected_today)
        self.assertEqual(my_request.period_end, expected_end_date)

    @patch.object(
        TaxReceiptGeneratorRequest, '_post_validate'
    )
    def test_validate_no_date(self, patch_post):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date=None, user_id=None, event_id=None)
        self.assertEqual(my_request.today.year, dt.today().year)
        self.assertEqual(my_request.today.month, dt.today().month)
        self.assertEqual(my_request.today.day, dt.today().day)

    @patch.object(
        TaxReceiptGeneratorRequest, '_post_validate'
    )
    def test_incorrect_format_date(self, patch_post):
        with self.assertRaises(IncorrectFormatDateException) as e:
            my_request = TaxReceiptGeneratorRequest(country='AR', today_date='21-s-2', user_id=None, event_id=None)
            self.assertEqual(
                e.message,
                'Date is not matching format YYYY-MM-DD'
            )

    def test_post_validate(self):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date='2020-05-11', user_id=None, event_id=None)

        self.assertEqual(my_request.period_start, dt(2020, 4, 1, 0, 0))
        self.assertEqual(my_request.period_end, dt(2020, 5, 1, 0, 0))


class TestTaxReceiptsGenerator(TestCase):
    """
        Unit test for tax_receipt_generator.TaxReceiptGenerator module
    """

    def setUp(self):
        self.my_generator = TaxReceiptGenerator(dry_run=True, do_logging=False)

    def test_init(self):
        self.assertTrue(self.my_generator.dry_run)
        self.assertFalse(self.my_generator.do_logging)
        self.assertIsInstance(self.my_generator.query, str)

    @patch.object(
        TaxReceiptGenerator, 'get_and_iterate_no_series_events'
    )
    @patch.object(
        TaxReceiptGenerator, 'get_and_iterate_child_events'
    )
    def test_run_calls(self, patch_childs, patch_no_series):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date=None, user_id=None, event_id=None)
        self.my_generator.run(my_request)
        self.assertTrue(patch_childs.called)
        self.assertTrue(patch_no_series.called)

    def test_run_w_user(self):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date=None, user_id=1, event_id=None)
        self.my_generator.run(my_request)
        self.assertEqual(self.my_generator.conditional_mask, 'AND `Events`.`uid` = 1')

    def test_run_w_event(self):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date=None, user_id=None, event_id=1)
        self.my_generator.run(my_request)
        self.assertEqual(self.my_generator.conditional_mask, 'AND `Events`.`id` = 1')

    def test_logging(self):
        my_generator_other = TaxReceiptGenerator(dry_run=True, do_logging=True)
        name_expected = 'financial_transactions'
        self.assertIsNotNone(my_generator_other.logger)
        self.assertEqual(my_generator_other.logger.name, name_expected)

    def test_localize_date(self):
        country_code = 'AR'
        tz = 'America/Argentina/Buenos_Aires'
        date = dt(2020, 03, 10, 0, 0)
        local_date = self.my_generator.localize_date(country_code, date)

        self.assertEqual(local_date.year, date.year)
        self.assertEqual(local_date.month, date.month)
        self.assertEqual(local_date.day, date.day)
        self.assertEqual(str(local_date.tzinfo), tz)

    @patch.object(
        TaxReceiptGenerator, 'get_query_results'
    )
    def test_get_and_iterate_no_series_query(self, patch_query):
        """Test what we're sending to the query"""
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': 'AR',
            'status_query': 100,
        }
        parent_mask = '(`Events`.`id` = `Payment_Options`.`event`)'
        self.my_generator.get_and_iterate_no_series_events(query_options_test)

        self.assertEqual(patch_query.call_args[0][0], query_options_test)
        self.assertIn(
            parent_mask,
            patch_query.call_args[0][1]
        )

    @patch.object(
        TaxReceiptGenerator, 'iterate_querys_results'
    )
    def test_get_and_iterate_no_series(self, patch_iterate):
        """Test what we're sending to iterate"""
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': 'AR',
            'status_query': 100,
        }
        self.my_generator.get_and_iterate_no_series_events(query_options_test)

        self.assertIsInstance(patch_iterate.call_args[0][0], list)
        self.assertEqual(
            patch_iterate.call_args[0][1],
            query_options_test['localize_start_date_query']
        )
        self.assertEqual(
            patch_iterate.call_args[0][2],
            query_options_test['localize_end_date_query']
        )

    @patch.object(
        TaxReceiptGenerator, 'get_query_results'
    )
    def test_get_and_iterate_child_query(self, patch_query):
        """Test what we're sending to the query"""
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': 'AR',
            'status_query': 100,
        }
        child_mask = '(`Events`.`event_parent` = `Payment_Options`.`event`)'
        self.my_generator.get_and_iterate_child_events(query_options_test)

        self.assertEqual(patch_query.call_args[0][0], query_options_test)
        self.assertIn(
            child_mask,
            patch_query.call_args[0][1]
        )

    @patch.object(
        TaxReceiptGenerator, 'iterate_querys_results'
    )
    def test_get_and_iterate_child(self, patch_iterate):
        """Test what we're sending to iterate"""
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': 'AR',
            'status_query': 100,
        }
        self.my_generator.get_and_iterate_child_events(query_options_test)

        self.assertIsInstance(patch_iterate.call_args[0][0], list)
        self.assertEqual(
            patch_iterate.call_args[0][1],
            query_options_test['localize_start_date_query']
        )
        self.assertEqual(
            patch_iterate.call_args[0][2],
            query_options_test['localize_end_date_query']
        )

    def test_get_query_results_ok(self):
        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': 'AR',
            'status_query': 100,
        }
        query_test = 'SELECT * FROM `Orders` WHERE `status` = 100'
        self.assertIsInstance(
            self.my_generator.get_query_results(query_options_test, query_test),
            list
        )

    @patch.object(
        TaxReceiptGenerator, 'generate_tax_receipts'
    )
    def test_iterate_querys_results(self, patch_generate):
        my_user = UserFactory.create()
        my_event = EventFactory.create(user=my_user)
        my_pay_opt = PaymentOptionsFactory.create(event=my_event)
        my_order = OrderFactory.create(event=my_event)

        query_options_test = {
            'localize_end_date_query': '2020-04-01',
            'localize_start_date_query': '2020-03-01',
            'declarable_tax_receipt_countries_query': 'AR',
            'status_query': 100,
        }

        parent_mask = '(`Events`.`id` = `Payment_Options`.`event`)'
        conditional_mask = ''
        query_to_send = self.my_generator.query.format(condition_mask=conditional_mask, parent_child_mask=parent_mask)

        results = self.my_generator.get_query_results(query_options_test, query_to_send)

        self.my_generator.iterate_querys_results(
            results,
            query_options_test['localize_start_date_query'],
            query_options_test['localize_end_date_query']
        )
        expected_len_payment_option = 8
        expected_len_event = 3
        expected_len_tax_receipt_orders = 4

        self.assertEqual(len(patch_generate.call_args[0][0]), expected_len_payment_option)
        self.assertIsInstance(patch_generate.call_args[0][0], dict)

        self.assertEqual(len(patch_generate.call_args[0][1]), expected_len_event)
        self.assertIsInstance(patch_generate.call_args[0][1], dict)

        self.assertEqual(patch_generate.call_args[0][2], query_options_test['localize_start_date_query'])
        self.assertEqual(patch_generate.call_args[0][3], query_options_test['localize_end_date_query'])

        self.assertEqual(len(patch_generate.call_args[0][4]), expected_len_tax_receipt_orders)
        self.assertIsInstance(patch_generate.call_args[0][4], dict)

    @patch.object(
        TaxReceiptGenerator, 'call_service'
    )
    def test_generate_tax_receipts(self, patch_service):
        pay_opt = {
            'epp_address1': '',
            'epp_address2': '',
            'epp_state': '',
            'epp_name_on_account': '',
            'epp_tax_identifier': 'ohesuvuehar',
            'epp_zip': '',
            'epp_country': 'AR',
            'epp_city': ''
        }
        event = {'currency': u'USD', 'user_id': 1, 'id': 1}
        tr_order = {
            'payment_transactions_count': 1,
            'total_tax_amount': Decimal('1.1'),
            'base_amount': Decimal('1.1'),
            'total_taxable_amount_with_tax_amount': Decimal('5.1')
        }

        self.my_generator.generate_tax_receipts(
            pay_opt,
            event,
            dt(2020, 3, 1, 0, 0),
            dt(2020, 4, 1, 0, 0),
            tr_order
        )
        expected_len_tax_receipt_orders = 27
        self.assertEqual(len(patch_service.call_args.args[0]['tax_receipt']), expected_len_tax_receipt_orders)

    def test_get_epp_tax_identifier_type(self):
        ar = 'AR'
        ar_tax_id = 'CUIT'
        ar_tax_ex = '20123456789'
        br = 'BR'
        br_tax_id_1 = 'CNPJ'
        br_tax_id_2 = 'CPF'
        br_tax_ex_g_eleven = '123456789011'
        br_tax_ex_l_eleven = '1234567890'

        self.assertEqual(
            self.my_generator.get_epp_tax_identifier_type(ar, ar_tax_ex),
            ar_tax_id
        )
        self.assertEqual(
            self.my_generator.get_epp_tax_identifier_type(br, br_tax_ex_g_eleven),
            br_tax_id_1
        )
        self.assertEqual(
            self.my_generator.get_epp_tax_identifier_type(br, br_tax_ex_l_eleven),
            br_tax_id_2
        )
        self.assertEqual(
            self.my_generator.get_epp_tax_identifier_type('CL', '213'),
            ''
        )

    @patch.object(
        TaxReceiptGenerator, 'localize_date', return_value='2020-04-01'
    )
    @patch.object(
        SlackConnection, 'post_message'
    )
    def test_slack_message(self, patch_slack, patch_date):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date=None, user_id=None, event_id=None)
        generator = TaxReceiptGenerator(dry_run=False, do_logging=False)
        generator.run(my_request)
        call_expected = 2
        self.assertEqual(patch_slack.call_count, call_expected)

    @patch.object(
        GenerationProccessMailReport, 'generation_send_email_report'
    )
    @patch.object(
        TaxReceiptGenerator, 'localize_date', return_value='2020-04-01'
    )
    @patch.object(
        SlackConnection, 'post_message'
    )
    def test_email_report(self, patch_slack, patch_date, patch_mail):
        my_request = TaxReceiptGeneratorRequest(country='AR', today_date=None, user_id=None, event_id=None)
        generator = TaxReceiptGenerator(dry_run=False, do_logging=False)
        generator.run(my_request)
        expected_called = 1
        self.assertEqual(patch_mail.call_count, expected_called)
        self.assertIsInstance(patch_mail.call_args[0][0], unicode)
        self.assertIsInstance(patch_mail.call_args[0][1], dt)
        self.assertIsInstance(patch_mail.call_args[0][2], dt)

    def test_integration(self):
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
        expected_called = 3
        my_request = TaxReceiptGeneratorRequest(
            country='AR',
            user_id=None,
            event_id=None,
            today_date='2020-04-11'
        )
        expected_called = 3
        self.my_generator.run(my_request)
        self.assertEqual(
            self.my_generator.cont_tax_receipts,
            expected_called
        )


class TestGenerateEntryPoint(TestCase):

    def test_not_configured_country(self):
        my_exc = CountryNotConfiguredException()
        with self.assertRaises(CommandError) as cm:
            call_command(generate_script_name, dry_run=True, country='CL')
        self.assertEqual(
            str(cm.exception),
            my_exc.message
        )

    def test_user_and_event(self):
        my_exc = UserAndEventProvidedException()
        with self.assertRaises(CommandError) as cm:
            call_command(generate_script_name, dry_run=True, country='AR', user_id=1, event_id=1)
        self.assertEqual(
            str(cm.exception),
            my_exc.message
        )

    def test_no_country(self):
        my_exc = NoCountryProvidedException()
        with self.assertRaises(CommandError) as cm:
            call_command(generate_script_name, dry_run=True)
        self.assertEqual(
            str(cm.exception),
            my_exc.message
        )

    def test_date_incorrect(self):
        my_exc = IncorrectFormatDateException()
        with self.assertRaises(CommandError) as cm:
            call_command(generate_script_name, dry_run=True, country='AR', today_date='12-s-12')
        self.assertEqual(
            str(cm.exception),
            my_exc.message
        )

    @patch(
        'invoicing_app.tax_receipt_generator.TaxReceiptGenerator.run'
    )
    def test_run(self, patch_run):
        call_command(generate_script_name, dry_run=True, country='AR')
        self.assertTrue(patch_run.called)
        self.assertEqual(patch_run.call_args[0][0].country, 'AR')
        self.assertIsNone(patch_run.call_args[0][0].user_id)
        self.assertIsNone(patch_run.call_args[0][0].event_id)
