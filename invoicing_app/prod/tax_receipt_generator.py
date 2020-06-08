import logging

from common.utils.slack import SlackConnection
from path_mail import GenerationProccessMailReport

from ebgeo.timezone import tzinfo
import pytz
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from django.db import connections

from decimal import Decimal

from django.conf import settings

from permissions.constants import PERMISSION_USER_PAYMENTS_USER_INSTRUMENTS
from permissions.noninteractive import get_noninteractive_token
from service import control

from ebapps import payments as payment_service_constants

SLACK_TOKEN = ''
SLACK_CHANNEL = ''
DB_NAME = 'slave'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

class TaxReceiptGenerator():

    def __init__(self, dry_run, do_logging):
        self.dry_run = dry_run
        self.do_logging = do_logging
        self.logger = logging.getLogger('financial_transactions')
        self.sentry = logging.getLogger('sentry')
        self.conditional_mask = ''
        self.cont_tax_receipts = 0
        self.error_cont = 0
        self.slack_notification = SlackConnection(SLACK_TOKEN)
        self.mail_report = GenerationProccessMailReport()
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
                INNER JOIN `Payment_Options` ON {parent_child_mask}
            WHERE (
                `Orders`.`status` = %(status_query)s AND
                `Orders`.`pp_date` <= %(localize_end_date_query)s AND
                `Orders`.`changed` >= %(localize_start_date_query)s AND
                `Orders`.`mg_fee` > '0.00' AND
                `Orders`.`changed` <= %(localize_end_date_query)s AND
                `Orders`.`pp_date` >= %(localize_start_date_query)s AND
                `Payment_Options`.`accept_eventbrite` = 1 AND
                `Payment_Options`.`epp_country` = %(declarable_tax_receipt_countries_query)s
                {condition_mask}
            )
            GROUP BY
                `event_id`
            ORDER BY NULL
        '''

    def run(self, request):
        """
            Run method executes all the business logic. The request attribute is an instance
            of the TaxReceiptGeneratorRequest class
        """
        if self.do_logging:
            self.enable_logging()

        if request.event_id:
            event_id = request.event_id
            self.conditional_mask = 'AND `Events`.`id` = {}'.format(event_id)
        elif request.user_id:
            user_id = request.user_id
            self.conditional_mask = 'AND `Events`.`uid` = {}'.format(user_id)

        localize_start_date = self.localize_date(
            request.country,
            request.period_start
        )
        localize_end_date = self.localize_date(
            request.country,
            request.period_end
        )

        query_options = {
            'localize_end_date_query': localize_end_date,
            'localize_start_date_query': localize_start_date,
            'declarable_tax_receipt_countries_query': request.country,
            'status_query': 100,
        }

        if not self.dry_run:
            self.slack_notification.post_message(
                channel=SLACK_CHANNEL,
                text='''
                    The generation script has started.
                    - Country: {country}
                    - Start date: {start}
                    - End date: {end}
                '''.format(country=request.country, start=request.period_start, end=request.period_end),
                username='tax_receipt_generator'
            )
        self.logger.info("Starting generate tax receipts")
        self.logger.info("Start date: {}".format(request.period_start))
        self.logger.info("End date: {}".format(request.period_end))
        self.get_and_iterate_no_series_events(query_options)
        self.get_and_iterate_child_events(query_options)
        self.logger.info("Tax receipts generated: {}".format(self.cont_tax_receipts))
        self.logger.info("Errors: {}".format(self.error_cont))
        self.logger.info("End Generation new tax receipts")
        self.logger.info("Ending generate tax receipts")
        if not self.dry_run:
            self.slack_notification.post_message(
                channel=SLACK_CHANNEL,
                text='''
                    The generation script has finished.
                    - Tax receipts generated: {generated}
                    - Errors: {errors}
                '''.format(generated=self.cont_tax_receipts, errors=self.error_cont),
                username='tax_receipt_generator'
            )
            self.mail_report.generation_send_email_report(
                request.country,
                request.period_start,
                request.period_end
            )

    def localize_date(self, country_code, date):
        event_timezone = pytz.country_timezones(country_code)[0]
        return dt(
            year=date.year,
            month=date.month,
            day=date.day,
            tzinfo=pytz.timezone(event_timezone)
        ).astimezone(tzinfo.get_default_tzinfo()).replace(tzinfo=None)

    def get_and_iterate_no_series_events(self, query_options):
        parent_mask = '(`Events`.`id` = `Payment_Options`.`event`)'
        query = self.query.format(condition_mask=self.conditional_mask, parent_child_mask=parent_mask)
        query_results = self.get_query_results(query_options, query)
        self.iterate_querys_results(
            query_results,
            query_options['localize_start_date_query'],
            query_options['localize_end_date_query'],
        )

    def get_and_iterate_child_events(self, query_options):
        child_mask = '(`Events`.`event_parent` = `Payment_Options`.`event`)'
        query = self.query.format(condition_mask=self.conditional_mask, parent_child_mask=child_mask)
        query_results = self.get_query_results(query_options, query)
        self.iterate_querys_results(
            query_results,
            query_options['localize_start_date_query'],
            query_options['localize_end_date_query'],
        )

    def get_query_results(self, query_options, query):
        query_results = []

        with connections[DB_NAME].cursor() as cursor:
            cursor.execute(
                query,
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
                if result['total_tax_amount'] is None:
                    result['total_tax_amount'] = Decimal('0.00')

                self.logger.info(
                    "Processing event: {event} total_taxable_amount_with_tax_amount: {ttawta} base_amount: {base_amount} total_tax_amount: {total_tax_amount} payment_transactions_count: {payment_trans_count}".format(
                        event=result['event_id'],
                        ttawta=str(tax_receipt_orders['total_taxable_amount_with_tax_amount']),
                        base_amount=str(tax_receipt_orders['base_amount']),
                        total_tax_amount=str(tax_receipt_orders['total_tax_amount']),
                        payment_trans_count=tax_receipt_orders['payment_transactions_count']
                    )
                )

                try:
                    self.generate_tax_receipts(
                        payment_option,
                        event,
                        localize_start_date,
                        localize_end_date,
                        tax_receipt_orders
                    )
                except Exception as e:
                    self._log_exception(e, event['id'])

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
            tax_receipt_orders['total_taxable_amount_with_tax_amount'] - tax_receipt_orders['total_tax_amount']
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
                'start_date_period': localize_start_date.strftime(DATE_FORMAT),
                'end_date_period': localize_end_date.strftime(DATE_FORMAT),
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
                    'start_date': localize_start_date.strftime(DATE_FORMAT),
                    'end_date': localize_end_date.strftime(DATE_FORMAT),
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
            client = control.Client('billing')
            job = client.new_job()
            auth_token = get_noninteractive_token([PERMISSION_USER_PAYMENTS_USER_INSTRUMENTS.value])['token']
            job.control.auth = auth_token
            job.create_tax_receipt(**orders_kwargs)
            response = client.send_job(job)
            if response.is_error():
                raise Exception(str(response.actions[0].error_detail))
            else:
                self.logger.info(
                    'Generated Tax Receipt: event: %i response: %s' % (
                        event['id'],
                        response,
                    )
                )
                self.cont_tax_receipts = self.cont_tax_receipts + 1
        else:
            self.call_service_dry_run()

    def call_service_dry_run(self):
        self.cont_tax_receipts = self.cont_tax_receipts + 1

    def get_epp_tax_identifier_type(self, epp_country, epp_tax_identifier):
        if not self.dry_run:
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

    def enable_logging(self):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(name)-12s: %(levelname)-8s %(message)s'
        )
        console.setFormatter(formatter)
        self.logger.addHandler(console)

    def _log_exception(self, e, event_id=None, quiet=False):
        message = 'Error in generate_tax_receipts, event: {} , details: {}, dry_run: {} '.format(
            event_id,
            e.message,
            self.dry_run
        )
        self.logger.error(message)
        self.error_cont = self.error_cont + 1


class TaxReceiptGeneratorRequest(object):

    def __init__(self, country, today_date, user_id, event_id):
        self.country = country
        self.today_date = today_date
        self.user_id = user_id
        self.event_id = event_id
        self._validate()
        self._post_validate()

    def _validate(self):
        """
            Check if the params passed to the tax_receipt_generator are ok.
        """
        if self.country:
            if self.country not in settings.EVENTBRITE_TAX_INFORMATION:
                raise CountryNotConfiguredException()
        else:
            raise NoCountryProvidedException()

        if self.user_id and self.event_id:
            raise UserAndEventProvidedException()

        if self.today_date:
            try:
                self.today = dt.strptime(self.today_date, '%Y-%m-%d')
            except Exception:
                raise IncorrectFormatDateException()
        else:
            self.today = dt.today()

    def _post_validate(self):
        """
            Set the fields after validation
        """
        curr_month = dt(self.today.year, self.today.month, 1)
        prev_month = curr_month - relativedelta(months=1)
        self.period_start = prev_month
        self.period_end = curr_month


class CountryNotConfiguredException(Exception):
    def __init__(self):
        self.message = 'The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)'
        super(CountryNotConfiguredException, self).__init__(self.message)


class UserAndEventProvidedException(Exception):
    def __init__(self):
        self.message = 'Can not use event and user options in the same time'
        super(UserAndEventProvidedException, self).__init__(self.message)


class NoCountryProvidedException(Exception):
    def __init__(self):
        self.message = 'No country provided. It provides: command --country="EX" (AR-Argentina or BR-Brazil)'
        super(NoCountryProvidedException, self).__init__(self.message)


class IncorrectFormatDateException(Exception):
    def __init__(self):
        self.message = 'Date is not matching format YYYY-MM-DD'
        super(IncorrectFormatDateException, self).__init__(self.message)
