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
from invoicing_app.circuitbreaker import CircuitBreaker


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

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._check_ARG_requirements',
    )
    def test_update_tax_receipts_that_met_requirements_arg(self, check_arg):
        country = 'AR'
        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.save()

        self.command.tax_receipts = [self.tax_receipt]
        self.command.update_tax_receipts_that_met_requirements()

        self.assertEqual(
            check_arg.call_args[0][0],
            self.tax_receipt
        )

        self.assertEqual(
            check_arg.call_args[0][1],
            self.payment_options
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._check_BR_requirements',
    )
    def test_update_tax_receipts_that_met_requirements_br(self, check_br):
        country = 'BR'
        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.save()

        self.command.tax_receipts = [self.tax_receipt]
        self.command.update_tax_receipts_that_met_requirements()

        self.assertEqual(
            check_br.call_args[0][0],
            self.tax_receipt
        )

        self.assertEqual(
            check_br.call_args[0][1],
            self.payment_options
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._update_tax_receipt',
    )
    def test_check_ARG_requirements(self, update_tax_receipt):
        country = 'AR'

        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.recipient_address = ''
        self.tax_receipt.recipient_name = ''
        self.tax_receipt.recipient_tax_identifier_number = ''
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.epp_address1 = 'address1'
        self.payment_options.epp_name_on_account = 'epp_name_on_account'
        self.payment_options.epp_zip = '2132'
        self.payment_options.epp_city = 'city'
        self.payment_options.epp_state = 'state'

        self.payment_options.save()

        self.command._check_ARG_requirements(self.tax_receipt, self.payment_options)

        self.assertEqual(
            update_tax_receipt.call_args[0][0].recipient_address,
            self.payment_options.epp_address1
        )

        self.assertEqual(
            update_tax_receipt.call_args[0][0].recipient_tax_identifier_number,
            self.payment_options.epp_tax_identifier
        )

        self.assertEqual(
            update_tax_receipt.call_args[0][0].recipient_name,
            self.payment_options.epp_name_on_account
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._update_tax_receipt',
    )
    def test_check_BR_requirements_zip_cpf(self, update_tax_receipt):
        country = 'BR'

        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.recipient_postal_code = ''
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.epp_address1 = 'address1'
        self.payment_options.epp_name_on_account = 'epp_name_on_account'
        self.payment_options.epp_zip = '2132'
        self.payment_options.epp_city = 'city'
        self.payment_options.epp_state = 'state'
        self.payment_options.epp_tax_identifier = ''.join(random.choice(string.lowercase) for _ in range(11))

        self.payment_options.save()

        self.command._check_BR_requirements(self.tax_receipt, self.payment_options)

        self.assertEqual(
            update_tax_receipt.call_args[0][0].recipient_postal_code,
            self.payment_options.epp_zip
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._update_tax_receipt',
    )
    def test_check_BR_requirements_zip_cnpj(self, update_tax_receipt):
        country = 'BR'

        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.recipient_postal_code = ''
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.epp_address1 = 'address1'
        self.payment_options.epp_name_on_account = 'epp_name_on_account'
        self.payment_options.epp_zip = '2132'
        self.payment_options.epp_city = 'city'
        self.payment_options.epp_state = 'state'
        self.payment_options.epp_tax_identifier = ''.join(random.choice(string.lowercase) for _ in range(12))

        self.payment_options.save()

        self.command._check_BR_requirements(self.tax_receipt, self.payment_options)

        self.assertEqual(
            update_tax_receipt.call_args[0][0].recipient_postal_code,
            self.payment_options.epp_zip
        )

    @patch(
        'invoicing_app.management.commands.update_incomplete_tax_receipts.Command._log_due_to_missing_to_info',
    )
    def test_check_ARG_requirements_error(self, log_due_to_missing_to_info):
        country = 'AR'
        self.command.verbose = True

        self.tax_receipt.reporting_country_code = country
        self.tax_receipt.recipient_address = ''
        self.tax_receipt.recipient_name = ''
        self.tax_receipt.recipient_tax_identifier_number = ''
        self.tax_receipt.save()

        self.payment_options.epp_country = country
        self.payment_options.epp_name_on_account = 'epp_name_on_account'
        self.payment_options.epp_zip = '2132'
        self.payment_options.epp_city = 'city'
        self.payment_options.epp_state = 'state'

        self.payment_options.save()

        self.command._check_ARG_requirements(self.tax_receipt, self.payment_options)

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
