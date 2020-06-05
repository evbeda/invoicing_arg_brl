from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from invoicing_app.models import TaxReceipt

from django.db.models import (
    Count,
    Sum,
)

from django.template.loader import render_to_string

DATE_FORMAT_REPORT = '%Y-%m-%d %H:%M:%S'

class GenerationProccessMailReport():

    def generation_send_email_report(self, country, period_start, period_end):
        start_date = period_start - relativedelta(days=1)
        end_date = period_end - relativedelta(seconds=1)

        report_data = TaxReceipt.objects.filter(
            reporting_country_code=country,
            start_date_period__range=(start_date, end_date),
        ).aggregate(
            count_id=Count('id'),
            gts=Sum('base_amount') / 100,
            gtf=Sum('total_taxable_amount') / 100,
        )
        rendered = render_to_string(
            'generation_template.html',
            {
                'period': start_date.strftime(DATE_FORMAT_REPORT) + ' - ' + end_date.strftime(DATE_FORMAT_REPORT),
                'country': country,
                'count_id': report_data['count_id'],
                'gts': report_data['gts'],
                'gtf': report_data['gtf'],
            }
        )
        # my_email_connection = EmailConnection()
        # my_email_connection.send_email(rendered)
        # print(rendered)
