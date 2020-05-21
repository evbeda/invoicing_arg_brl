from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
from django.db import connections
from invoicing_app.models import PaymentOptions, Event, TaxReceipt


class Command(BaseCommand):

    help = ('Change status of the tax receipts that have every requirement from INCOMPLETE to PENDING')

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
        self.arg_requirements = base_requirements# + ("tax_regime_type_id",)
        self.br_requirements = base_requirements + ("recipient_postal_code",)
        self.CPF_CHAR_COUNT_LIMIT = 11
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, **options):
        print("----Finding tax receipts that meet requiremente criteria----")
        self.find_incomplete_tax_receipts()
        self.update_tax_receipts_that_met_requirements()
        print("----Updated process completed.----")

    def find_incomplete_tax_receipts(self):
        self.tax_receipts = TaxReceipt.objects.using('billing_local')\
            .filter(status_id=TaxReceiptStatuses.get_id_from_name("INCOMPLETE"),
                    reporting_country_code__in=['AR', 'BR']).iterator()

    def update_tax_receipts_that_met_requirements(self):
        for tax_receipt in self.tax_receipts:
            po = PaymentOptions.objects.using('default').get(event=tax_receipt.event_id)
            if tax_receipt.reporting_country_code == 'AR':
                self.__check_ARG_requirements(tax_receipt, po)
            else:
                self.__check_BR_requirements(tax_receipt, po)

    def __check_ARG_requirements(self, tax_receipt, payment_option):
        # IF ONE FIELD FAILS CHECK REQUIREMENTS, WE CANT CHANGE TO 'PENDING' STATUS
        # SO ITS POINTLESS TO KEEP CHECKING REST OF FIELDS.
        for requirement in self.arg_requirements:
            po_attribute = getattr(payment_option, str(self.tax_to_po_requirement_dict.get(requirement)), '')
            if self.__check_single_requirement(po_attribute):
                setattr(tax_receipt, requirement, po_attribute)
            else:
                return
        self.__update_tax_receipt(tax_receipt)

    def __check_BR_requirements(self, tax_receipt, payment_option):
        # CHECK IF BR TAX AUTHORITY IS CPNJ OR CPF, BECAUSE THEY USE DIFFERENT REQUIREMENTS.
        if self.__get_epp_tax_identifier_type(payment_option.epp_tax_identifier) == 'CNPJ':
            for requirement in self.br_requirements + ('recipient_city',):
                po_attribute = getattr(payment_option, str(self.tax_to_po_requirement_dict.get(requirement)), '')
                if self.__check_single_requirement(po_attribute):
                    setattr(tax_receipt, requirement, po_attribute)
                else:
                    return
            self.__update_tax_receipt(tax_receipt)

        elif self.__get_epp_tax_identifier_type(payment_option.epp_tax_identifier) == 'CPF':
            for requirement in self.br_requirements:
                po_attribute = getattr(payment_option, str(self.tax_to_po_requirement_dict.get(requirement)), '')
                if self.__check_single_requirement(po_attribute):
                    setattr(tax_receipt, requirement, po_attribute)
                else:
                    return
            self.__update_tax_receipt(tax_receipt)

    def __check_single_requirement(self, po_attr):
        return po_attr == ''

    def __update_tax_receipt(self, tax_receipt):
        tax_receipt.status_id = TaxReceiptStatuses.get_id_from_name("PENDING")
        tax_receipt.save(using='billing_local', force_update=True)


    def __get_epp_tax_identifier_type(self, epp_tax_identifier): #
        if len(epp_tax_identifier) > self.CPF_CHAR_COUNT_LIMIT:
            return 'CNPJ'
        else:
            return 'CPF'
        return ''


class TaxReceiptStatuses:
    @staticmethod
    def get_id_from_name(string):
        if string is "INCOMPLETE":
            return 1
        elif string is 'PENDING':
            return 2
