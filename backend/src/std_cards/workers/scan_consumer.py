from std_cards.core.geoip import lookup_geo
from std_cards.core.nats.consumer import ConsumerConfig, NatsMessage, build_pull_consumer
from std_cards.core.ua import parse_ua
from std_cards.models.analytics import ScanEvent

consumer = build_pull_consumer(
    ConsumerConfig(
        consumer_name="scan-worker",
        jetstream_name="CARDS_SCAN",
        filter_subjects=["cards.scan.recorded"],
        fetch_size=100,
        ack_wait_seconds=60.0,
        max_ack_pending=200,
        max_deliver=5,
    )
)


@consumer.consume("scan_recorded", data_model_in=ScanEvent, timeout=30.0)
async def _handle_scan(message: NatsMessage[ScanEvent]) -> None:
    from std_cards.db.session import get_session_maker
    from std_cards.infrastructure.repositories.scan_repo import ScanEventRepository

    ev = message.data
    ua_info = parse_ua(ev.user_agent)
    country, city, lat, lon = lookup_geo(ev.ip)

    sm = get_session_maker()
    repo = ScanEventRepository(sm)
    await repo.insert_batch(
        [
            {
                "card_id": ev.card_id,
                "ts": ev.ts,
                "ip": ev.ip,
                "user_agent": ev.user_agent,
                "device_type": ua_info.device_type,
                "os_family": ua_info.os_family,
                "browser_family": ua_info.browser_family,
                "country_code": country,
                "city": city,
                "lat": lat,
                "lon": lon,
                "referer": ev.referer,
                "is_bot": ua_info.is_bot,
            }
        ]
    )
