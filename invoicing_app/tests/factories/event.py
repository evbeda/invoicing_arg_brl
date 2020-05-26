import factory
from user import UserFactory


class EventFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.Event'
        django_get_or_create = (
            'event_name',
            'series',
            'user',
            'event_parent',
            'currency',
            'repeat_schedule',
        )

    event_name = 'event_test'
    series = False
    user = UserFactory.create()
    event_parent = None
    currency = 'ARS'
    repeat_schedule = ''
