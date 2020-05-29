import factory


class UserTaxRegimesFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.Users_Tax_Regimes'
        django_get_or_create = ('tax_regime_type_id', 'user_id')

    user_id = 0
    tax_regime_type_id = 0
