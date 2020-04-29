import factory


class EventFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'invoicing_app.Event'
        django_get_or_create = (
            'event_name',
            'is_series_parent',
            'user',
            'event_parent',
            'currency',
        )

    event_name = 'EVENT_1'
    is_series_parent = False
    user = None
    event_parent = None
    currency = 'USD'
