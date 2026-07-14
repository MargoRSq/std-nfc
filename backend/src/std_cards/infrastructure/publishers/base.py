from std_cards.core.nats.publisher import NatsPublisher


class NatsPublisherApi:
    """Базовый класс для публикации событий по доменам.

    Subclass per domain (CardsPublishApi, ImportsPublishApi, ScansPublishApi).
    Subject и message_type фиксируются в subclass-методах.
    """

    def __init__(self, publisher: NatsPublisher) -> None:
        self.publisher = publisher
