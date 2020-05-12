from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging

from decimal import Decimal

import pytz

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from invoicing import settings

from django.db import connection

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class Command(BaseCommand):
    """
        This is a temporary process that retrieve order information of Brazil events
        for generate tax receipts.
        This process will be redo at hadoop (Oozie+Hive).

        djmanage generate_tax_receipts --settings=settings.configuration

        for event:
        djmanage generate_tax_receipts --event=18388067 --settings=settings.configuration

        for user:
        djmanage generate_tax_receipts --user=150335768 --settings=settings.configuration

        use --logging to enable logger in console

        use --dry_run to test the command but don't update any DB or call any service

        use --country to process an specific country

    """
    help = ('Generate end of month tax receipts')

    option_list = BaseCommand.option_list + (
        make_option(
            '--date',
            dest='today_date',
            type='string',
            help='Force a specific date: YYYY-MM-DD format',
        ),
        make_option(
            '--event',
            dest='event_id',
            type='int',
            help='Enter a event ID',
        ),
        make_option(
            '--user',
            dest='user_id',
            type='int',
            help='Enter a user ID',
        ),
        make_option(
            '--dry_run',
            action="store_true",
            dest='dry_run',
            default=False,
            help='If set, nothing will be written to DB tables.',
        ),
        make_option(
            '--logging',
            action="store_true",
            dest="logging",
            default=False,
            help='Enable logger in console',
        ),
        make_option(
            '--country',
            dest="country",
            default=False,
            help='specific country to process (like AR or BR)',
        ),
    )

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('financial_transactions')
        self.event_id = None
        self.user_id = None
        self.sentry = logging.getLogger('sentry')
        self.query = '''
                    SELECT
                        `Orders`.`event` as `event_id`,
                        `Events`.`uid` as `user_id`,
                        `Events`.`event_parent` as `event_parent`,
                        `Events`.`currency` as `currency`,
                        `Payment_Options`.`epp_country` as `epp_country`,
                        `Payment_Options`.`epp_name_on_account` as `epp_name_on_account`,
                        `Payment_Options`.`epp_address1` as `epp_address1`,
                        `Payment_Options`.`epp_address2` as `epp_address2`,
                        `Payment_Options`.`epp_zip` as `epp_zip`,
                        `Payment_Options`.`epp_city` as `epp_city`,
                        `Payment_Options`.`epp_state` as `epp_state`,
                        `Payment_Options`.`epp_tax_identifier` as `epp_tax_identifier`,
                        COUNT(`Orders`.`event`) AS `payment_transactions_count`,
                        SUM(`Orders`.`eb_tax`) AS `total_tax_amount`,
                        SUM(`Orders`.`mg_fee`) AS `total_taxable_amount_with_tax_amount`,
                        SUM(`Orders`.`gross`) AS `base_amount`
                    FROM `Orders`
                        INNER JOIN `Events` ON (`Orders`.`event` = `Events`.`id` )
                        INNER JOIN `Payment_Options` ON PARENT_CHILD_MASK
                    WHERE (
                        `Orders`.`status` = %(status_query)s AND
                        `Orders`.`pp_date` <= %(localize_end_date_query)s AND
                        `Orders`.`changed` >= %(localize_start_date_query)s AND
                        `Orders`.`mg_fee` > '0.00' AND
                        `Orders`.`changed` <= %(localize_end_date_query)s AND
                        `Orders`.`pp_date` >= %(localize_start_date_query)s AND
                        `Payment_Options`.`accept_eventbrite` = 1 AND
                        `Payment_Options`.`epp_country` = %(declarable_tax_receipt_countries_query)s
                        CONDITION_MASK
                    )
                    GROUP BY
                        `event_id`
                    ORDER BY NULL
                '''
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, **options):

        if options['country']:
            if options['country'] not in settings.EVENTBRITE_TAX_INFORMATION:
                raise CommandError(
                    'The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)'
                )
            self.declarable_tax_receipt_countries = str(options['country'])
        else:
            raise CommandError(
                'No country provided. It provides: command --country="EX" (AR-Argentina or BR-Brazil)'
            )

        if options['user_id'] and options['event_id']:
            raise CommandError('Can not use both options in the same time')

        if options['today_date']:
            try:
                today = dt.strptime(options['today_date'], '%Y-%m-%d')
                self.period_end = dt(today.year, today.month, today.day)
            except Exception:
                raise CommandError("Date is not matching format YYYY-MM-DD")
        else:
            today = dt.today()

        curr_month = dt(today.year, today.month, 1)
        prev_month = curr_month - relativedelta(months=1)
        self.period_start = prev_month
        self.period_end = curr_month

        if options['logging']:
            self.enable_logging()

        if options['event_id']:
            self.event_id = options['event_id']
            self.query = self.query.replace(
                'CONDITION_MASK',
                'AND `Events`.`id` = ' + str(self.event_id)
            )

        if options['user_id']:
            self.user_id = options['user_id']
            self.query = self.query.replace(
                'CONDITION_MASK',
                'AND `Events`.`uid` = ' + str(self.user_id)
            )

        # If there isn't condition, remove the CONDITION MASK from the query
        if (not options['user_id']) and (not options['event_id']):
            self.query = self.query.replace(
                'CONDITION_MASK',
                ''
            )

        self.dry_run = options['dry_run']
        self.logger.info("------Starting generate tax receipts------")
        self.logger.info("start: {}".format(self.period_start))
        self.logger.info("end: {}".format(self.period_end))

        localize_start_date = self.localize_date(
            self.declarable_tax_receipt_countries,
            self.period_start
        )
        localize_end_date = self.localize_date(
            self.declarable_tax_receipt_countries,
            self.period_end
        )

        query_options = {
            'localize_end_date_query': localize_end_date,
            'localize_start_date_query': localize_start_date,
            'declarable_tax_receipt_countries_query': self.declarable_tax_receipt_countries,
            'status_query': 100,
        }

        self.get_and_iterate_no_series_events(query_options)
        self.get_and_iterate_child_events(query_options)
        self.logger.info("------End Generation new tax receipts------")
        self.logger.info("------Ending generate tax receipts------")

    def _log_exception(self, e, event_id=None, quiet=False):
        message = 'Error in generate_tax_receipts, event: {} , details: {}, dry_run: {} '.format
        (
            event_id,
            e.message,
            self.dry_run
        )
        if not quiet:
            self.sentry.error('Error in generate_tax_receipts',
                              extra={
                                  'view': 'generate_tax_receipts',
                                  'data': {
                                      'exception': e,
                                      'event': event_id,
                                  }
                              })
            self.logger.error(message)

    def localize_date(self, country_code, date):
        event_timezone = pytz.country_timezones(country_code)[0]
        return dt(
            year=date.year,
            month=date.month,
            day=date.day,
            tzinfo=pytz.timezone(event_timezone)
        )

    def get_and_iterate_no_series_events(self, query_options):
        # Replace of PARENT_CHILD_MASK for the no-series condition in INNER JOIN
        self.query = self.query.replace(
            'PARENT_CHILD_MASK',
            '(`Events`.`id` = `Payment_Options`.`event`)'
        )
        query_results = self.get_query_results(query_options)
        self.iterate_querys_results(
            query_results,
            query_options['localize_start_date_query'],
            query_options['localize_end_date_query'],
        )
        # Undo the replacing of PARENT_CHILD_MASK for the child events
        self.query = self.query.replace(
            '(`Events`.`id` = `Payment_Options`.`event`)',
            'PARENT_CHILD_MASK'
        )

    def get_and_iterate_child_events(self, query_options):
        self.query = self.query.replace(
            'PARENT_CHILD_MASK',
            '(`Events`.`event_parent` = `Payment_Options`.`event`)'
        )
        # Can't use a mask here, so replace a entire WHERE condition
        self.query = self.query.replace(
            '`Payment_Options`.`accept_eventbrite` = 1 AND',
            '`Payment_Options`.`accept_eventbrite` = 1 AND `Events`.`event_parent` IS NOT NULL AND',
        )

        query_results = self.get_query_results(query_options)

        self.iterate_querys_results(
            query_results,
            query_options['localize_start_date_query'],
            query_options['localize_end_date_query'],
        )

        self.query = self.query.replace(
            '(`Events`.`event_parent` = `Payment_Options`.`event`)',
            'PARENT_CHILD_MASK'
        )

    def get_query_results(self, query_options):
        query_results = []

        with connection.cursor() as cursor:
            cursor.execute(
                self.query,
                query_options
            )
            response = cursor.fetchall()

            columns = [col[0] for col in cursor.description]
            for row in response:
                data = {}
                for index, item in enumerate(row):
                    if not data.get(row[0], False):
                        data[columns[index]] = row[index]
                query_results.append(data)
            return query_results

    def iterate_querys_results(self, query_results, localize_start_date, localize_end_date):
        for result in query_results:

            payment_option = {
                'epp_country': result['epp_country'],
                'epp_name_on_account': result['epp_name_on_account'],
                'epp_address1': result['epp_address1'],
                'epp_address2': result['epp_address2'],
                'epp_zip': result['epp_zip'],
                'epp_city': result['epp_city'],
                'epp_state': result['epp_state'],
                'epp_tax_identifier': result['epp_tax_identifier'],
            }

            event = {
                'id': result['event_id'],
                'user_id': result['user_id'],
                'currency': result['currency'],
            }

            tax_receipt_orders = {
                'payment_transactions_count': result['payment_transactions_count'],
                'total_tax_amount': result['total_tax_amount'],
                'base_amount': result['base_amount'],
                'total_taxable_amount_with_tax_amount': result['total_taxable_amount_with_tax_amount']
            }

            if result['payment_transactions_count'] > 0:
                # EB-28811: some eb_tax in DB has Null
                if result['total_tax_amount'] is None:
                    result['total_tax_amount'] = Decimal('0.00')

                self.logger.info(
                    ('Processing event: %i total_taxable_amount_with_tax_amount: %s ' +
                     'base_amount: %s total_tax_amount: %s ' +
                     'payment_transactions_count: %i dry_run: %s') % (
                        result['event_id'],
                        str(tax_receipt_orders['total_taxable_amount_with_tax_amount']),
                        str(tax_receipt_orders['base_amount']),
                        str(tax_receipt_orders['total_tax_amount']),
                        tax_receipt_orders['payment_transactions_count'],
                        self.dry_run,
                    )
                )

                self.generate_tax_receipts(
                    payment_option,
                    event,
                    localize_start_date,
                    localize_end_date,
                    tax_receipt_orders
                )

    def generate_tax_receipts(
            self,
            payment_option,
            event,
            localize_start_date,
            localize_end_date,
            tax_receipt_orders
    ):
        EB_TAX_INFO = settings.EVENTBRITE_TAX_INFORMATION[payment_option['epp_country']]
        if not EB_TAX_INFO:
            raise Exception('Cannot find EVENTBRITE_TAX_INFORMATION in settings')
        total_taxable_amount = (
                tax_receipt_orders['total_taxable_amount_with_tax_amount'] -
                tax_receipt_orders['total_tax_amount']
        )
        orders_kwargs = {
            'tax_receipt': {
                'user_id': str(event['user_id']),
                'event_id': str(event['id']),
                'reporting_country_code': payment_option['epp_country'],
                'currency': event['currency'],
                'base_amount': {
                    'value': int(tax_receipt_orders['base_amount'] * 100),
                    'currency': event['currency'],
                },
                'total_taxable_amount': {
                    'value': int(total_taxable_amount * 100),
                    'currency': event['currency'],
                },
                'payment_transactions_count': tax_receipt_orders['payment_transactions_count'],
                'start_date_period': localize_start_date,
                'end_date_period': localize_end_date,
                'description': '',
                'supplier_type': 'EVENTBRITE',
                'supplier_name': EB_TAX_INFO['supplier_name'],
                'supplier_address': EB_TAX_INFO['supplier_address'],
                'supplier_address_2': EB_TAX_INFO['supplier_address_2'],
                'supplier_postal_code': EB_TAX_INFO['supplier_postal_code'],
                'supplier_city': EB_TAX_INFO['supplier_city'],
                'supplier_region': EB_TAX_INFO['supplier_region'],
                'supplier_tax_information': {
                    'tax_identifier_type': EB_TAX_INFO['tax_identifier_type'],
                    'tax_identifier_country': payment_option['epp_country'],
                    'tax_identifier_number': EB_TAX_INFO['tax_identifier_number'],
                },
                'recipient_name': payment_option['epp_name_on_account'],
                'recipient_type': 'ORGANIZER',
                'recipient_address': payment_option['epp_address1'],
                'recipient_address_2': payment_option['epp_address2'],
                'recipient_postal_code': payment_option['epp_zip'],
                'recipient_city': payment_option['epp_city'],
                'recipient_region': payment_option['epp_state'],
                'tax_receipt_period_details': [{
                    'reference_type': 'ORDER',
                    'start_date': localize_start_date,
                    'end_date': localize_end_date,
                    'tax_rate': 0,
                    'base_amount': {
                        'value': int(tax_receipt_orders['base_amount'] * 100),
                        'currency': event['currency'],
                    },
                    'taxable_amount': {
                        'value': int(total_taxable_amount * 100),
                        'currency': event['currency'],
                    },
                }],
            }
        }

        if payment_option['epp_tax_identifier']:
            orders_kwargs['tax_receipt']['recipient_tax_information'] = {
                'tax_identifier_type': self.get_epp_tax_identifier_type(
                    payment_option['epp_country'],
                    payment_option['epp_tax_identifier']
                ),
                'tax_identifier_country': payment_option['epp_country'],
                'tax_identifier_number': payment_option['epp_tax_identifier'],
            }

        if not self.dry_run:
            from service import control
            from permissions.constants import PERMISSION_USER_PAYMENTS_USER_INSTRUMENTS
            from permissions.noninteractive import get_noninteractive_token
            client = control.Client('billing')
            job = client.new_job()
            auth_token = get_noninteractive_token([PERMISSION_USER_PAYMENTS_USER_INSTRUMENTS.value])['token']
            job.control.auth = auth_token
            job.create_tax_receipt(**orders_kwargs)
            response = client.send_job(job)
            if response.is_error():
                raise Exception(response.error_detail)
            else:
                self.logger.info(
                    'Generated Tax Receipt: event: %i response: %s' % (
                        event.id,
                        response,
                    )
                )
        else:
            self.call_service(orders_kwargs)

    def enable_logging(self):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(name)-12s: %(levelname)-8s %(message)s'
        )
        console.setFormatter(formatter)
        self.logger.addHandler(console)

    def call_service(self, orders_kwargs):
        pass

    def get_epp_tax_identifier_type(self, epp_country, epp_tax_identifier):
        if not self.dry_run:
            from eb_constants import payment_service_constants
            cpf_char_count_limit = payment_service_constants.CPF_CHAR_COUNT_LIMIT
        else:
            cpf_char_count_limit = 11

        if epp_country == 'BR':
            if len(epp_tax_identifier) > cpf_char_count_limit:
                return 'CNPJ'
            else:
                return 'CPF'
        if epp_country == 'AR':
            return 'CUIT'

        return ''
