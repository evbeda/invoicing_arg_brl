from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
from django.db.models import Sum, Count, Q
from decimal import Decimal

import pytz

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from invoicing import settings

from invoicing_app.models import PaymentOptions, Event, Order
from memory_profiler import profile
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
            '--quiet',
            dest='quiet',
            action='store_true',
            help='Disable debug logging',
        ),
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
            '--test',
            dest='test',
            default=False,
            help='will run appending all de out dicts in a list'
        )
    )

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('financial_transactions')
        self.event_id = None
        self.user_id = None
        self.sentry = logging.getLogger('sentry')
        self.test_set = {}

        super(Command, self).__init__(*args, **kwargs)

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

        # localize_start_date = dt.strptime('2020-03-01', '%Y-%m-%d')
        # localize_end_date = dt.strptime('2020-04-01', '%Y-%m-%d')
        # 00:00:00-03:54
        localize_start_date = str(dt(2020, 03, 01, 0, 0))
        localize_end_date = str(dt(2020, 04, 01, 0, 0))
        # localize_start_date = str(self.localice_date(
        #     payment_option.epp_country,
        #     self.period_start
        # ))
        # localize_end_date = str(self.localice_date(
        #     payment_option.epp_country,
        #     self.period_end
        # ))

        if options['test']:
            self.test = True

        if options['country']:
            if options['country'] not in settings.EVENTBRITE_TAX_INFORMATION:
                raise CommandError(
                    'The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)'
                )
            self.declarable_tax_receipt_countries = [options['country']]
        else:
            # keys at settings.EVENTBRITE_TAX_INFORMATION are country codes
            self.declarable_tax_receipt_countries = settings.EVENTBRITE_TAX_INFORMATION.keys()
        # event = 1194
        query_results = Order.objects.select_related('event', 'event___paymentoptions').filter(
            status=100,
            pp_date__gte=dt.strptime('2020-03-01', '%Y-%m-%d'),
            pp_date__lte=dt.strptime('2020-04-01', '%Y-%m-%d'),
            changed__gte=dt.strptime('2020-03-01', '%Y-%m-%d'),
            changed__lte=dt.strptime('2020-04-01', '%Y-%m-%d'),
            mg_fee__gt=Decimal('0.00'),
            event___paymentoptions__epp_country__in=('AR', 'BR'),
            event___paymentoptions__accept_eventbrite=True,


        ).values(
            'event_id',
            'event__user_id',
            'event___paymentoptions__epp_country',
            'event__currency',
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
        )

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

    # ver que hacer con los hijos
    # def generate_tax_receipt_per_payment_options(self, payment_options):
    #     for payment_option in payment_options:
    #         try:
    #             if payment_option.event.is_series_parent:
    #                 child_events = Event.objects.filter(
    #                     event_parent=payment_option.event.id
    #                 ).iterator()
    #                 for child_event in child_events:
    #                     self.generate_tax_receipt_event(payment_option, child_event)
    #             else:
    #                 self.generate_tax_receipt_event(payment_option, payment_option.event)
    #
    #         except Exception as e:
    #             raise self._log_exception(e)

    def _log_exception(self, e, event_id=None, quiet=False):
        # Don't throw all to sentry, only the important2
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
        if self.test:
            self.test_set.update({orders_kwargs['tax_receipt']['event_id']: orders_kwargs})
