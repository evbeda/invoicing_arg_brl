import factory


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.User'
        django_get_or_create = ('username',)

    username = 'FACTORY_USER_1'
