import factory


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.User'
        django_get_or_create = ('first_name',)

    first_name = 'FACTORY_USER_1'
