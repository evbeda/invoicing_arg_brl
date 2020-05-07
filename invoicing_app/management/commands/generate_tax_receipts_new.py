from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging

from django.db.models import (
    Count,
    Q,
    Sum,
)

from decimal import Decimal

import pytz

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from invoicing import settings

from invoicing_app.models import Order

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
        make_option(
            '--podict',
            dest="use_po_dict",
            default=True,
            help='flag to use or not a dict'
                 ' for cache the result of payment options of parents events',
        ),
    )

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('financial_transactions')
        self.event_id = None
        self.user_id = None
        self.sentry = logging.getLogger('sentry')
        self.parent_payment_options = {}

        super(Command, self).__init__(*args, **kwargs)

    def localize_date(self, country_code, date):
        event_timezone = pytz.country_timezones(country_code)[0]
        return dt(
            year=date.year,
            month=date.month,
            day=date.day,
            tzinfo=pytz.timezone(event_timezone)
        )

    def handle(self, **options):
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

        if options['country']:
            if options['country'] not in settings.EVENTBRITE_TAX_INFORMATION:
                raise CommandError(
                    'The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)'
                )
            self.declarable_tax_receipt_countries = [options['country']]
        else:
            self.declarable_tax_receipt_countries = settings.EVENTBRITE_TAX_INFORMATION.keys()

        self.dry_run = options['dry_run']

        if options['logging']:
            self.enable_logging()
        if options['event_id']:
            self.event_id = options['event_id']
        if options['user_id']:
            self.user_id = options['user_id']

        self.logger.info("------Starting generate tax receipts------")
        self.logger.info("start: {}".format(self.period_start))
        self.logger.info("end: {}".format(self.period_end))

        # If the country is not specified, 'AR' will be set
        localize_start_date = self.localize_date(
            self.declarable_tax_receipt_countries[0],
            self.period_start
        )
        localize_end_date = self.localize_date(
            self.declarable_tax_receipt_countries[0],
            self.period_end
        )

        optional_filter = []

        if self.event_id:
            optional_filter.append(Q(event=self.event_id))

        if self.user_id:
            optional_filter.append(Q(event__user=self.user_id))

        query_results = Order.objects.select_related('event', 'event___paymentoptions').filter(
            status=100,
            pp_date__gte=localize_start_date,
            pp_date__lte=localize_end_date,
            changed__gte=localize_start_date,
            changed__lte=localize_end_date,
            mg_fee__gt=Decimal('0.00'),
            event___paymentoptions__epp_country__in=self.declarable_tax_receipt_countries,
            event___paymentoptions__accept_eventbrite=True,
            *optional_filter
        ).values(
            'event_id',
            'event__user_id',
            'event__event_parent',
            'event__currency',
            'event___paymentoptions__epp_country',
            'event___paymentoptions__epp_name_on_account',
            'event___paymentoptions__epp_address1',
            'event___paymentoptions__epp_address2',
            'event___paymentoptions__epp_zip',
            'event___paymentoptions__epp_city',
            'event___paymentoptions__epp_state',
        ).annotate(
            base_amount=Sum('gross'),
            total_taxable_amount_with_tax_amount=Sum('mg_fee'),
            total_tax_amount=Sum('eb_tax'),
            payment_transactions_count=Count('event'),
        ).iterator()

        with connection.cursor() as cursor:
            cursor.execute(
                '''
                    SELECT
                        `Orders`.`event` AS `event_id`,
                        `Events`.`uid` AS `event__user_id`,
                        `Payment_Options`.`epp_country` AS `event___paymentoptions__epp_country`,
                        `Events`.`currency` AS `event__currency`,
                        `Payment_Options`.`epp_name_on_account` AS `event___paymentoptions__epp_name_on_account`,
                        `Payment_Options`.`epp_address1` AS `event___paymentoptions__epp_address1`,
                        `Payment_Options`.`epp_address2` AS `event___paymentoptions__epp_address2`,
                        `Payment_Options`.`epp_zip` AS `event___paymentoptions__epp_zip`,
                        `Payment_Options`.`epp_city` AS `event___paymentoptions__epp_city`,
                        `Payment_Options`.`epp_state` AS `event___paymentoptions__epp_state`,
                        `Events`.`event_parent` AS `event__event_parent`,
                        COUNT(`Orders`.`event`) AS `payment_transactions_count`,
                        SUM(`Orders`.`eb_tax`) AS `total_tax_amount`,
                        SUM(`Orders`.`mg_fee`) AS `total_taxable_amount_with_tax_amount`,
                        SUM(`Orders`.`gross`) AS `base_amount`
                    FROM `Orders`
                        INNER JOIN `Events` ON (`Orders`.`event` = `Events`.`id` )
                        INNER JOIN `Payment_Options` ON (`Events`.`event_parent` = `Payment_Options`.`event`)
                    WHERE (
                        `Orders`.`status` = 100 AND
                        `Orders`.`pp_date` <= '2020-04-01 00:00:00' AND
                        `Orders`.`changed` >= '2020-03-01 00:00:00' AND
                        `Orders`.`mg_fee` > '0.00' AND
                        `Orders`.`changed` <= '2020-04-01 00:00:00' AND
                        `Orders`.`pp_date` >= '2020-03-01 00:00:00' AND
                        `Payment_Options`.`accept_eventbrite` = 1 AND
                        `Payment_Options`.`epp_country` IN ('AR', 'BR') AND
                        `Events`.`event_parent` IS NOT NULL
                    )
                    GROUP BY
                        `Orders`.`event`
                    ORDER BY NULL
                '''
            )
            response = []
            columns = [col[0] for col in cursor.description]
            query_results_child = cursor.fetchall()
            for row in query_results_child:
                data = {}
                for index, item in enumerate(row):
                    if not data.get(row[0], False):
                        data[columns[index]] = row[index]
                response.append(data)

        self.iterate_querys_results(query_results, localize_start_date, localize_end_date)
        self.iterate_querys_results(response, localize_start_date, localize_end_date)

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

    def iterate_querys_results(self, query_results, localize_start_date, localize_end_date):
        for result in query_results:

            payment_option = {
                'epp_country': result['event___paymentoptions__epp_country'],
                'epp_name_on_account': result['event___paymentoptions__epp_name_on_account'],
                'epp_address1': result['event___paymentoptions__epp_address1'],
                'epp_address2': result['event___paymentoptions__epp_address2'],
                'epp_zip': result['event___paymentoptions__epp_zip'],
                'epp_city': result['event___paymentoptions__epp_city'],
                'epp_state': result['event___paymentoptions__epp_state']
            }

            event = {
                'id': result['event_id'],
                'user_id': result['event__user_id'],
                'currency': result['event__currency'],
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

        self.call_service(orders_kwargs)

    def call_service(self, orders_kwargs):
        pass
