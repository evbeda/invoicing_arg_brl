from __future__ import absolute_import

from datetime import datetime as dt
import logging
from optparse import make_option

from dateutil.relativedelta import relativedelta
from django.db import close_old_connections
from django.template.loader import render_to_string
from django.db.models import (
    Count,
    Sum,
)

try:
    # Local
    from invoicing import settings
    from django.core.management.base import BaseCommand, CommandError
    from invoicing_app.models import TaxReceipt
    # from invoicing_app.models import TaxReceiptStatuses
except Exception:
    # For production
    from django.conf import settings
    from common.management.base import BaseCommand
    from django.core.management.base import CommandError
    from ebutils.collections import chunks
    from permissions.constants.permissions import PERMISSION_USER_BILLING_CHARGE_SCHEDULES_READ
    from service import control
    from billing_service.common.auth import get_cron_auth_token
    from billing_service.common.logger import get_logger
    from billing_service.models.lookup import TaxReceiptStatuses
    from billing_service.models.tax_receipts import TaxReceipt

DATE_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    """
        Command that search pending tax receipts and send them to declare.

        ./manage declare_pending_tax_receipts

        for currency:
        ./manage declare_pending_tax_receipts --currency=BRL

        for event:
        ./manage declare_pending_tax_receipts --event=18388067

        for user:
        ./manage declare_pending_tax_receipts --user=150335768

        use --logging to enable logger in console

        use --dry_run to test the command but don't update any DB or call any service

    """

    help = "Declara pending tax receipts"

    option_list = BaseCommand.option_list + (
        make_option(
            "--currency",
            dest="currency",
            type="string",
            help="Force declaration for specified currency",
        ),
        make_option("--event", dest="event_id", type="int", help="Only declare taxes for this event id"),
        make_option("--user_id", dest="user_id", type="int", help="Only declare taxes for this user id"),
        make_option(
            "--start_date_period",
            dest="start_date_period",
            type="string",
            help="Force a specific date: YYYY-MM-DD format",
        ),
        make_option(
            "--end_date_period", dest="end_date_period", type="string", help="Force a specific date: YYYY-MM-DD format"
        ),
        make_option(
            "--month_range",
            action="store",
            dest="month_range",
            default=1,
            metavar="MONTHS",
            help="How many months we should take into account if we dont specify start date / end date",
        ),
        make_option(
            "--dry_run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="If set, nothing will be written to DB tables."
        ),
        make_option("--logging", action="store_true", dest="logging", default=False, help="Enable logger in console"),
    )

    def __init__(self, *args, **kwargs):
        try:
            # For Production
            self.logger = get_logger()
        except Exception:
            # For Local
            self.logger = logging.getLogger('financial_transactions')
        self.month_range = relativedelta(months=1)
        self.start_date_period = None
        self.end_date_period = None
        self.currency = None
        self.event_id = None
        self.user_id = None

        super(Command, self).__init__(*args, **kwargs)

    def handle(self, **options):
        self.dry_run = options["dry_run"]

        if options["month_range"]:
            self.month_range = relativedelta(months=int(options.get("month_range")))

        if options.get("start_date_period"):
            try:
                today = dt.strptime(options["start_date_period"], DATE_FORMAT)
                self.start_date_period = dt(today.year, today.month, today.day)
            except Exception:
                raise CommandError("Start Date Period is not matching format YYYY-MM-DD")

        if options.get("end_date_period"):
            try:
                today = dt.strptime(options["end_date_period"], DATE_FORMAT)
                self.end_date_period = dt(today.year, today.month, today.day)
            except Exception:
                raise CommandError("End Date Period is not matching format YYYY-MM-DD")

        if self.start_date_period and not self.end_date_period:
            self.end_date_period = self.start_date_period + self.month_range

        elif not self.start_date_period and self.end_date_period:
            self.start_date_period = self.end_date_period - self.month_range

        if options.get("currency"):
            self.currency = options["currency"]

        if options.get("event_id"):
            self.event_id = options["event_id"]

        if options.get("user_id"):
            self.user_id = options["user_id"]

        if options.get("logging"):
            self.enable_logging()

        self.logger.info("------Starting Process------")
        if self.currency:
            self.logger.info("currency: %s" % self.currency)
        if self.event_id:
            self.logger.info("event id: %s" % self.event_id)
        if self.user_id:
            self.logger.info("user id: %s" % self.user_id)
        if self.start_date_period:
            self.logger.info("start_date_period: %s" % self.start_date_period)
        if self.end_date_period:
            self.logger.info("end_date_period: %s" % self.end_date_period)

        self.logger.info("------Starting declare pending tax receipts------")
        self.declare_pending_tax_receipts()
        self.logger.info("------Ending declare pending tax receipts------")
        self.logger.info("------Starting generate and send report------")
        self.send_email_report()
        self.logger.info("------Ending generate and send report------")
        self.logger.info("------Ending Process------")

    def declare_pending_tax_receipts(self):
        try:
            find_args = {"status_id": TaxReceiptStatuses.get_id_from_name("PENDING")}
            if self.currency:
                find_args["currency"] = self.currency
            if self.event_id:
                find_args["event_id"] = self.event_id
            if self.user_id:
                find_args["user_id"] = self.user_id

            if self.start_date_period:
                find_args["start_date_period__gte"] = self.start_date_period
            if self.end_date_period:
                find_args["end_date_period__lte"] = self.end_date_period

            tax_receipt_ids = TaxReceipt.objects.filter(**find_args).values_list("id", flat=True)

            if not self.dry_run:
                client = control.Client("billing")

                for tax_receipt_ids_batch in chunks(tax_receipt_ids, settings.TAX_RECEIPTS_BATCH_TO_DECLARE):
                    close_old_connections()

                    job = client.new_job()
                    job.control.auth = get_cron_auth_token(PERMISSION_USER_BILLING_CHARGE_SCHEDULES_READ)

                    job.declare_tax_receipts(
                        tax_receipt_ids=[str(tax_receipt_id) for tax_receipt_id in tax_receipt_ids_batch]
                    )
                    response = client.send_job(job)

                    if response.is_error():
                        raise Exception(
                            u"Failed to declare tax receipts: {error}".format(error=response.pretty_error())
                        )

        except Exception as e:

            message = "Error in declare_tax_receipts: details: {}, dry_run: {}".format(str(e), self.dry_run)
            self.logger.error(message)

    def enable_logging(self):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
        console.setFormatter(formatter)
        self.logger.addHandler(console)


    def send_email_report(self):
        start_date = self.start_date_period - relativedelta(days=1)
        end_date = self.end_date_period - relativedelta(seconds=1)

        report_data = TaxReceipt.objects.filter(
            currency=self.currency,
            start_date_period__range=(start_date, end_date),
            # status_id=TaxReceiptStatuses.get_id_from_name("PROCESSED"),
            status_id=3,
        ).aggregate(
            count_id=Count('id'),
            declared_gtf=Sum('total_taxable_amount') / 100,
        )

        rendered = render_to_string(
            'declaration_template.html',
            {
                'period': start_date.strftime(DATE_FORMAT)+' - ' +end_date.strftime(DATE_FORMAT),
                'currency': self.currency,
                'declared_gtf': report_data['declared_gtf'],
            }
        )
        print(rendered)
