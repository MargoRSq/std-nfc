from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from std_cards.core.nats.consumer import NatsMessage
from std_cards.models.analytics import ScanEvent
from std_cards.workers.scan_consumer import _handle_scan


@pytest.fixture
def scan_event() -> ScanEvent:
    return ScanEvent(
        card_id=uuid4(),
        ts=datetime.now(UTC),
        ip="1.2.3.4",
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        referer="https://example.com",
    )


async def test_handle_scan_calls_insert(scan_event: ScanEvent, session_maker):
    msg = AsyncMock(spec=NatsMessage)
    msg.data = scan_event

    mock_repo = AsyncMock()
    mock_repo.insert_batch = AsyncMock(return_value=1)

    with (
        patch("std_cards.db.session.get_session_maker", return_value=session_maker),
        patch(
            "std_cards.infrastructure.repositories.scan_repo.ScanEventRepository",
            return_value=mock_repo,
        ),
    ):
        await _handle_scan(msg)

    mock_repo.insert_batch.assert_called_once()
    call_args = mock_repo.insert_batch.call_args[0][0]
    assert len(call_args) == 1
    row = call_args[0]
    assert row["card_id"] == scan_event.card_id
    assert row["ip"] == "1.2.3.4"
    assert row["device_type"] == "mobile"
    assert row["is_bot"] is False


async def test_handle_scan_bot_detection(session_maker):
    event = ScanEvent(
        card_id=uuid4(),
        ts=datetime.now(UTC),
        ip="9.9.9.9",
        user_agent="Googlebot/2.1 (+http://www.google.com/bot.html)",
    )
    msg = AsyncMock(spec=NatsMessage)
    msg.data = event

    mock_repo = AsyncMock()
    mock_repo.insert_batch = AsyncMock(return_value=1)

    with (
        patch("std_cards.db.session.get_session_maker", return_value=session_maker),
        patch(
            "std_cards.infrastructure.repositories.scan_repo.ScanEventRepository",
            return_value=mock_repo,
        ),
    ):
        await _handle_scan(msg)

    row = mock_repo.insert_batch.call_args[0][0][0]
    assert row["is_bot"] is True
    assert row["device_type"] == "bot"


async def test_handle_scan_no_ua(session_maker):
    event = ScanEvent(card_id=uuid4(), ts=datetime.now(UTC))
    msg = AsyncMock(spec=NatsMessage)
    msg.data = event

    mock_repo = AsyncMock()
    mock_repo.insert_batch = AsyncMock(return_value=1)

    with (
        patch("std_cards.db.session.get_session_maker", return_value=session_maker),
        patch(
            "std_cards.infrastructure.repositories.scan_repo.ScanEventRepository",
            return_value=mock_repo,
        ),
    ):
        await _handle_scan(msg)

    row = mock_repo.insert_batch.call_args[0][0][0]
    assert row["device_type"] == "other"
    assert row["is_bot"] is False
