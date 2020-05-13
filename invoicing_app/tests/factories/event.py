import factory


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

    event_name = 'EVENT_1'
    series = False
    user = None
    event_parent = None
    currency = 'USD'
    repeat_schedule = ''
