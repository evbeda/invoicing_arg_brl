from django.core.management.base import BaseCommand
from django.db import connections
from invoicing_app.models import PaymentOptions, Event, TaxReceipt
import logging
from optparse import make_option


class Command(BaseCommand):
    help = ('Change status of the tax receipts that have every requirement from INCOMPLETE to PENDING')

    option_list = BaseCommand.option_list + (
        make_option(
            '--verbose',
            dest='verbose',
            action='store_true',
            help='Enable more logging information to stdout',
        ),
        make_option(
            '--dry_run',
            dest='dry_run',
            action='store_true',
            help='Run script against QA without writing to DB, if this arg is not used it will run against localhost',
        ),
    )

    def __init__(self, *args, **kwargs):
        self.tax_receipts = []

        base_requirements = (
            "recipient_name",
            "recipient_address",
            "recipient_tax_identifier_number",
        )
        self.tax_to_po_requirement_dict = {
            "recipient_name": "epp_name_on_account",
            "recipient_address": "epp_address1",
            "recipient_tax_identifier_number": "epp_tax_identifier",
            "recipient_postal_code": "epp_zip",
            "recipient_city": "epp_city",
            "tax_regime_type_id": "",
        }
        self.arg_requirements = base_requirements
        self.br_requirements = base_requirements + ("recipient_postal_code",)
        self.CPF_CHAR_COUNT_LIMIT = 11
        self.__configure_logger()
        self.logger = logging.getLogger(__name__)
        self.verbose = False
        self.dry_run = False
        self.invoicing = 'default'
        self.billing = 'billing_local'
        self.count = 0
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, **options):
        if options['verbose']:
            self.verbose = True
        if options['dry_run']:
            self.dry_run = True
            self.invoicing = 'invoicing_EB'
            self.billing = 'billing_EB'

        if self.verbose:
            self._log_hosts_being_used()
        self.logger.info("Finding tax receipts that meet requirements criteria")
        self.find_incomplete_tax_receipts()
        self.update_tax_receipts_that_met_requirements()

        if self.dry_run:
            self.logger.info("Tax receipts that can be updated: {}".format(self.count))
            self.logger.info("Finished update process in dry_run mode")
        else:
            self.logger.info("Updated {} tax receipts to PENDING".format(self.count))
            self.logger.info("Update process completed.")

    def find_incomplete_tax_receipts(self):
        try:
            self.tax_receipts = TaxReceipt.objects.using(self.billing)\
                .filter(
                status_id=TaxReceiptStatuses.get_id_from_name("INCOMPLETE"),
                reporting_country_code__in=['AR', 'BR'],
                ).iterator()
        except Exception as e:
            self._log_exception(e)
            raise e

    def update_tax_receipts_that_met_requirements(self):
        for tax_receipt in self.tax_receipts:
            try:
                po = PaymentOptions.objects.using(self.invoicing).get(event=tax_receipt.event_id)
                if tax_receipt.reporting_country_code == 'AR':
                    self._check_ARG_requirements(tax_receipt, po)
                else:
                    self._check_BR_requirements(tax_receipt, po)
            except Exception as e:
                self._log_exception(e, txr_id=tax_receipt.id, evnt_id=tax_receipt.event_id)

    def _check_ARG_requirements(self, tax_receipt, payment_option):
        # IF ONE FIELD FAILS CHECK REQUIREMENTS, WE CANT CHANGE TO 'PENDING' STATUS
        # SO ITS POINTLESS TO KEEP CHECKING REST OF FIELDS.
        for requirement in self.arg_requirements:
            po_attribute = getattr(payment_option, str(self.tax_to_po_requirement_dict.get(requirement)), '')
            if self.__check_single_requirement(po_attribute):
                setattr(tax_receipt, requirement, po_attribute)
            else:
                if self.verbose:
                    self._log_due_to_missing_to_info(
                        tax_receipt.id,
                        payment_option.id,
                        self.tax_to_po_requirement_dict[requirement],
                        po_attribute
                    )
                return
        self._update_tax_receipt(tax_receipt)

    def _check_BR_requirements(self, tax_receipt, payment_option):
        # CHECK IF BR TAX AUTHORITY IS CPNJ OR CPF, BECAUSE THEY USE DIFFERENT REQUIREMENTS.
        if self._get_epp_tax_identifier_type(payment_option.epp_tax_identifier) == 'CNPJ':
            for requirement in self.br_requirements + ('recipient_city',):
                po_attribute = getattr(payment_option, str(self.tax_to_po_requirement_dict.get(requirement)), '')
                if self.__check_single_requirement(po_attribute):
                    setattr(tax_receipt, requirement, po_attribute)
                else:
                    if self.verbose:
                        self._log_due_to_missing_to_info(
                            tax_receipt.id,
                            payment_option.id,
                            self.tax_to_po_requirement_dict[requirement],
                            po_attribute
                        )
                    return
            self._update_tax_receipt(tax_receipt)

        elif self._get_epp_tax_identifier_type(payment_option.epp_tax_identifier) == 'CPF':
            for requirement in self.br_requirements:
                po_attribute = getattr(payment_option, str(self.tax_to_po_requirement_dict.get(requirement)), '')
                if self.__check_single_requirement(po_attribute):
                    setattr(tax_receipt, requirement, po_attribute)
                else:
                    if self.verbose:
                        self._log_due_to_missing_to_info(
                            tax_receipt.id,
                            payment_option.id,
                            self.tax_to_po_requirement_dict[requirement],
                            po_attribute
                        )
                    return
            self._update_tax_receipt(tax_receipt)

    def __check_single_requirement(self, po_attr):
        return po_attr != ''

    def _update_tax_receipt(self, tax_receipt):
        if self.verbose:
            self.logger.info("Tax receipt with id:{} met every requirement."
                             .format(tax_receipt.id))
        tax_receipt.status_id = TaxReceiptStatuses.get_id_from_name("PENDING")
        self.count += 1
        if not self.dry_run:
            tax_receipt.save(using=self.billing, force_update=True)
            self.logger.info("Tax receipt with id:{} updated succesfully"
                             .format(tax_receipt.id))

    def _get_epp_tax_identifier_type(self, epp_tax_identifier):  #
        if len(epp_tax_identifier) > self.CPF_CHAR_COUNT_LIMIT:
            return 'CNPJ'
        else:
            return 'CPF'

    def _log_exception(self, e, txr_id=None, evnt_id=None):
        if txr_id:
            self.logger.error('''Tax Receipt with id:{} failed.
                                 Couldn't find associated Payment Option through the TaxReceipt.event={}'''
                              .format(txr_id, evnt_id))
        self.logger.error(e.message)

    def _log_due_to_missing_to_info(self, tax_id, po_id, requirement, po_attribute):
        self.logger.\
            info('''
                    Couldn't update status of tax receipt with id: {} to PENDING,
                    due to missing information on its associated payment option with id: {}.
                    The field that failed is PaymentOption.{}
                    Its value is: '{}', and it needs to be completed'''
                 .format(tax_id,
                         po_id,
                         requirement,
                         po_attribute)
                 )

    def _log_hosts_being_used(self):
        for db in (self.invoicing, self.billing):
            self.logger.info("Using {}. Host name: {}, Database name: {}".format(
                    db,
                    connections.databases[db]['HOST'],
                    connections.databases[db]['NAME']
                )
            )

    def __configure_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('--- %(name)s - %(levelname)s - %(message)s ---')
        ch.setFormatter(formatter)
        logger.addHandler(ch)


class TaxReceiptStatuses:
    @staticmethod
    def get_id_from_name(string):
        if string == "INCOMPLETE":
            return 1
        elif string == 'PENDING':
            return 2

