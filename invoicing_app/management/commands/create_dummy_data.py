from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

try:
    from invoicing_app.models import Order, PaymentOptions, User, Event
except Exception as e:
    from ebapps.orders.models import Order
    from ebapps.payments.models import PaymentOptions
    from ebapps.ebauth.models.user import User
    from ebapps.events.models.event import Event

from django.db import connection

import random
import string

try:
    from invoicing_app.tests.factories.user import UserFactory
    from invoicing_app.tests.factories.event import EventFactory
    from invoicing_app.tests.factories.paymentoptions import PaymentOptionsFactory
    from invoicing_app.tests.factories.order import OrderFactory
except Exception as e:
    from common.factories.events_factories import EventFactory
    from common.factories.payments_factories import EPPPaymentOptionsFactory
    from common.factories.orders_factories import OrderFactory
    from common.factories.ebauth_factories import UserFactory

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):

    """
        This is a script for create dummy data in production. Isn't performant, but
        meets his goal.
        Run with --clean_db for clean your db and then create dummy data
        Run with --quantity for specify the number of objects you want to create (required)
        This script isn't part of the project, is only for run the generate_tax_receipts_new.py
        in a local enviroment.
    """

    help = ('Create dummy Events, Orders, Users and PaymentOptions')

    option_list = BaseCommand.option_list + (
        make_option(
            '--clean_db',
            action="store_true",
            dest='clean_db',
            default=False,
            help='Clean db'
        ),
        make_option(
            '--quantity',
            dest='quantity',
            type='int',
            help='Enter a quantity'
        ),
    )

    def handle(self, **options):
        if options['quantity']:
            self.quantity = options['quantity']
        else:
            raise CommandError('Please, make sure to enter a number of objects to create: --quantity=X')

        if options['clean_db']:
            self.delete_all_models()

        today = dt.today()
        prev_date = dt(today.year, today.month, 1) - relativedelta(months=1)
        self.date_in = str(dt(today.year, prev_date.month, 12))
        self.date_out = str(dt(2015, 05, 22, 0, 0))

        self.user_test = UserFactory.create(
            first_name='user_test'
        )

        self.insert_columns_in_data_base(self.quantity, self.date_in, self.user_test)
        self.insert_series_event(self.user_test)

        print('Objects created ok!')

    def delete_all_models(self):
        self.delete_model_data(Order)
        self.delete_model_data(PaymentOptions)
        self.delete_model_data(Event)
        self.delete_model_data(User)
        print("Database cleaned")

    def delete_model_data(self, model_class):
        cursor = connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        table_name = model_class._meta.db_table
        sql = "DELETE FROM %s WHERE 1;" % (table_name,)
        cursor.execute(sql)
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

    def insert_columns_in_data_base(self, quantity, date, user_test):
        event_list = []

        for index in range(quantity):
            event = EventFactory.create(
                name='event_{}'.format(index),
                series=False,
                user=user_test,
                currency='ARS',
                paymentoptions__epp_country='AR',
                paymentoptions__epp_name_on_account='name_test',
                paymentoptions__epp_address1='address1',
                paymentoptions__epp_address2='addres2',
                paymentoptions__epp_zip='5500',
                paymentoptions__epp_city='city_test',
                paymentoptions__epp_state='state_test',
                paymentoptions__epp_tax_identifier='LOZG7802117B9',
            )
            event_list.append(event)

            OrderFactory.create(
                status=100,
                pp_date=date,
                changed=date,
                event=event,
                mg_fee=5.1,
                gross=1.1,
                eb_tax=1.1,
            )

    def insert_series_event(self, user_1):
        event_parent_1 = EventFactory.create(
            name='event_parent_1',
            user=user_1,
            currency='ARS'
        )

        event_parent_1.series = True
        event_parent_1.repeat_schedule = ''
        event_parent_1.save()
        # --------------------------------------------- #
        event_child_1 = EventFactory.create(
            name='event_child_1',
            user=user_1,
            event_parent=event_parent_1,
            currency='ARS'
        )

        order_child_1 = OrderFactory.create(
            event=event_child_1,
            pp_date=self.date_in,
            changed=self.date_in,
        )
        # --------------------------------------------- #
        event_child_2 = EventFactory.create(
            name='event_child_2',
            user=user_1,
            event_parent=event_parent_1,
            currency='ARS'
        )

        order_child_2 = OrderFactory.create(
            event=event_child_1,
            pp_date=self.date_in,
            changed=self.date_in,
        )
        # --------------------------------------------- #
        event_child_3 = EventFactory.create(
            name='event_child_3',
            user=user_1,
            event_parent=event_parent_1,
            currency='ARS'
        )

        order_child_3 = OrderFactory.create(
            event=event_child_1,
            pp_date=str(dt(2019, 12, 8, 0, 0)),
            changed=str(dt(2019, 12, 8, 0, 0)),
        )
