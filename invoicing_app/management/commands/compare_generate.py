from django.core.management.base import BaseCommand
from optparse import make_option
from invoicing_app.management.commands.generate_tax_receipts_old import Command as CommandOld
from invoicing_app.management.commands.generate_tax_receipts_new import Command as CommandNew

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
            '--country',
            dest="country",
            default=False,
            help='specific country to process (like AR or BR)',
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
    )

    def handle(self, *args, **options):
        options_to_commands = {
            'user_id': None,
            'dry_run': options['dry_run'],
            'settings': None,
            'event_id': None,
            'pythonpath': None,
            'verbosity': 1,
            'traceback': False,
            'quiet': False,
            'today_date': options['today_date'],
            'no_color': False,
            'country': options['country'],
            'logging': options['logging'],
            'compare': True
        }

        self.my_command = CommandOld()
        self.my_command_new = CommandNew()

        self.my_command.handle(**options_to_commands)
        dict_old = self.my_command.get_dict_return()
        print 'OLD SCRIPT'
        print len(dict_old)
        self.my_command_new.handle(**options_to_commands)
        dict_new = self.my_command_new.get_dict_return()
        print 'NEW SCRIPT'
        print len(dict_new)

        if dict_new == dict_old:
            print 'igual'
        else:
            print 'diferente'