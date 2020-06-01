from django.core.management.base import (
    BaseCommand,
    CommandError
)
from optparse import make_option
import logging
from invoicing_app.tax_receipt_generator import (
    CountryNotConfiguredException,
    IncorrectFormatDateException,
    NoCountryProvidedException,
    TaxReceiptGenerator,
    UserAndEventProvidedException,
)


class Command(BaseCommand):
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
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('--- %(name)s - %(levelname)s - %(message)s ---')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, **options):
        tax_receipt_generator_for_ar = TaxReceiptGenerator(options)
        try:
            tax_receipt_generator_for_ar.run()
        except CountryNotConfiguredException:
            raise CommandError('The country provided is not configured (settings.EVENTBRITE_TAX_INFORMATION)')
        except UserAndEventProvidedException:
            raise CommandError('Can not use event and user options in the same time')
        except NoCountryProvidedException:
            raise CommandError('No country provided. It provides: command --country="EX" (AR-Argentina or BR-Brazil)')
        except IncorrectFormatDateException:
            raise CommandError('Date is not matching format YYYY-MM-DD')
