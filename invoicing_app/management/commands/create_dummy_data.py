from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

from invoicing_app.models import Order, PaymentOptions, User, Event

from django.db import connection

import random
import string

from invoicing_app.tests.factories.user import UserFactory
from invoicing_app.tests.factories.event import EventFactory
from invoicing_app.tests.factories.paymentoptions import PaymentOptionsFactory
from invoicing_app.tests.factories.order import OrderFactory

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):

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
                event_name='event_{}'.format(index),
                is_series_parent=False,
                series=False,
                user=user_test,
                currency='ARS',
                repeat_schedule=''
            )
            event_list.append(event)

            pay_opt = PaymentOptionsFactory.create(
                epp_country='AR',
                accept_eventbrite=True,
                event=event_list[index],
                epp_name_on_account='name_test',
                epp_address1='address1',
                epp_address2='addres2',
                epp_zip='5500',
                epp_city='city_test',
                epp_state='state_test',
                epp_tax_identifier=''.join(random.choice(string.lowercase) for x in range(random.randint(11, 12)))
            )

            order = OrderFactory.create(
                status=100,
                pp_date=date,
                changed=date,
                event=event_list[index],
                mg_fee=5.1,
                gross=1.1,
                eb_tax=1.1,
            )

    def insert_series_event(self, user_1):
        event_parent_1 = EventFactory.create(
            event_name='event_parent_1',
            user=user_1,
            currency='ARS'
        )

        pay_opt_parent_1 = PaymentOptionsFactory.create(
            event=event_parent_1
        )

        event_parent_1.series = True
        event_parent_1.repeat_schedule = ''
        event_parent_1.save()
        # --------------------------------------------- #
        event_child_1 = EventFactory.create(
            event_name='event_child_1',
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
            event_name='event_child_2',
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
            event_name='event_child_3',
            user=user_1,
            event_parent=event_parent_1,
            currency='ARS'
        )

        order_child_3 = OrderFactory.create(
            event=event_child_1,
            pp_date=str(dt(2019, 12, 8, 0, 0)),
            changed=str(dt(2019, 12, 8, 0, 0)),
        )
