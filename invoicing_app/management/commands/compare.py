from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from invoicing_app.management.commands.generate_tax_receipts_new import Command as CommandOld
from invoicing_app.tax_receipt_generator import (
    CountryNotConfiguredException,
    IncorrectFormatDateException,
    NoCountryProvidedException,
    TaxReceiptGenerator,
    TaxReceiptGeneratorRequest,
    UserAndEventProvidedException
)


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--date',
            dest='today_date',
            type='string',
            help='Force a specific date: YYYY-MM-DD format',
        ),
        make_option(
            '--country',
            dest="country",
            default=False,
            help='specific country to process (like AR or BR)',
        ),
        make_option(
            '--logging',
            action="store_true",
            dest="logging",
            default=False,
            help='Enable logger in console',
        ),
    )

    def handle(self, *args, **options):
        options_to_commands = {
            'user_id': None,
            'dry_run': True,
            'settings': None,
            'event_id': None,
            'pythonpath': None,
            'verbosity': 1,
            'traceback': False,
            'quiet': False,
            'today_date': options['today_date'],
            'no_color': False,
            'country': 'AR',
            'logging': options['logging'],
            'compare': True
        }

        self.new_results = self.run_new(options_to_commands)
        self.old_results = self.run_old(options_to_commands)

        if self.new_results == self.old_results:
            print('BOTHS SCRIPTS THROWS THE SAME RESULTS')
        else:
            print('THERE ARE DIFFERENCES BETWEEN THE RESULTS')

    def run_new(self, options_to_commands):
        tax_generator = TaxReceiptGenerator(
            dry_run=options_to_commands['dry_run'],
            do_logging=options_to_commands['logging']
        )
        try:
            request = TaxReceiptGeneratorRequest(
                event_id=options_to_commands['event_id'],
                user_id=options_to_commands['user_id'],
                country=options_to_commands['country'],
                today_date=options_to_commands.get('today_date'),
            )
        except CountryNotConfiguredException as e:
            raise CommandError(e.message)
        except UserAndEventProvidedException as e:
            raise CommandError(e.message)
        except NoCountryProvidedException as e:
            raise CommandError(e.message)
        except IncorrectFormatDateException as e:
            raise CommandError(e.message)

        tax_generator.run(request)

        return tax_generator.output_dict

    def run_old(self, options_to_commands):
        my_command = CommandOld()
        my_command.handle(**options_to_commands)
        return my_command.output_dict
