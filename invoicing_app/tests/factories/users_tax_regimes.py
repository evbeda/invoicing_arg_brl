import factory


class UserTaxRegimesFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.Users_Tax_Regimes'
        django_get_or_create = ()
