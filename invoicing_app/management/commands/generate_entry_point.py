from django.core.management.base import (
    BaseCommand,
    CommandError
)
from optparse import make_option

from invoicing_app.tax_receipt_generator import (
    CountryNotConfiguredException,
    IncorrectFormatDateException,
    NoCountryProvidedException,
    TaxReceiptGenerator,
    TaxReceiptGeneratorRequest,
    UserAndEventProvidedException
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

    def handle(self, **options):

        tax_generator_for_ar = TaxReceiptGenerator(
            dry_run=options['dry_run'],
            do_logging=options['logging']
        )
        try:
            request = TaxReceiptGeneratorRequest(
                event_id=options['event_id'],
                user_id=options['user_id'],
                country=options['country'],
                today_date=options.get('today_date'),
            )
        except CountryNotConfiguredException as e:
            raise CommandError(e.message)
        except UserAndEventProvidedException as e:
            raise CommandError(e.message)
        except NoCountryProvidedException as e:
            raise CommandError(e.message)
        except IncorrectFormatDateException as e:
            raise CommandError(e.message)

        tax_generator_for_ar.run(request)
