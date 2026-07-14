import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from std_cards.core.exceptions import NotFoundError
from std_cards.infrastructure.repositories.admin_card_groups_repo import AdminCardGroupRepository
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.scan_repo import ScanEventRepository
from std_cards.models.analytics import (
    CardAnalytics,
    DashboardKpi,
    DashboardResponse,
    DeviceStats,
    RegionStats,
    TimelinePoint,
    TopActiveUser,
    TopActiveUsersResponse,
    TopCard,
)
from std_cards.models.auth import UserDB, UserRole
from std_cards.services.card_service import build_acl_filter

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60.0

EN_TO_RU_CITY: dict[str, str] = {
    "Moscow": "Москва",
    "Saint Petersburg": "Санкт-Петербург",
    "St Petersburg": "Санкт-Петербург",
    "St. Petersburg": "Санкт-Петербург",
    "Novosibirsk": "Новосибирск",
    "Yekaterinburg": "Екатеринбург",
    "Ekaterinburg": "Екатеринбург",
    "Kazan": "Казань",
    "Nizhny Novgorod": "Нижний Новгород",
    "Chelyabinsk": "Челябинск",
    "Samara": "Самара",
    "Omsk": "Омск",
    "Rostov-on-Don": "Ростов-на-Дону",
    "Ufa": "Уфа",
    "Krasnoyarsk": "Красноярск",
    "Voronezh": "Воронеж",
    "Perm": "Пермь",
    "Volgograd": "Волгоград",
    "Krasnodar": "Краснодар",
    "Saratov": "Саратов",
    "Tyumen": "Тюмень",
    "Tolyatti": "Тольятти",
    "Izhevsk": "Ижевск",
    "Barnaul": "Барнаул",
    "Ulyanovsk": "Ульяновск",
    "Irkutsk": "Иркутск",
    "Khabarovsk": "Хабаровск",
    "Yaroslavl": "Ярославль",
    "Vladivostok": "Владивосток",
    "Makhachkala": "Махачкала",
    "Tomsk": "Томск",
    "Orenburg": "Оренбург",
    "Kemerovo": "Кемерово",
    "Novokuznetsk": "Новокузнецк",
    "Ryazan": "Рязань",
    "Astrakhan": "Астрахань",
    "Penza": "Пенза",
    "Lipetsk": "Липецк",
    "Tula": "Тула",
    "Kirov": "Киров",
    "Cheboksary": "Чебоксары",
    "Kaliningrad": "Калининград",
    "Bryansk": "Брянск",
    "Kursk": "Курск",
    "Ivanovo": "Иваново",
    "Magnitogorsk": "Магнитогорск",
    "Tver": "Тверь",
    "Stavropol": "Ставрополь",
    "Belgorod": "Белгород",
    "Sochi": "Сочи",
    "Simferopol": "Симферополь",
    "Sevastopol": "Севастополь",
    "Madrid": "Мадрид",
    "Paris": "Париж",
    "Berlin": "Берлин",
    "London": "Лондон",
    "Rome": "Рим",
    "Amsterdam": "Амстердам",
    "Vienna": "Вена",
    "Prague": "Прага",
    "Warsaw": "Варшава",
    "Minsk": "Минск",
    "Kiev": "Киев",
    "Kyiv": "Киев",
    "Almaty": "Алматы",
    "Tashkent": "Ташкент",
    "Yerevan": "Ереван",
    "Tbilisi": "Тбилиси",
    "Baku": "Баку",
    "New York": "Нью-Йорк",
    "Beijing": "Пекин",
    "Tokyo": "Токио",
    "Istanbul": "Стамбул",
}


def _localize_region(region: str | None) -> str | None:
    if region is None:
        return None
    return EN_TO_RU_CITY.get(region, region)


class AnalyticsService:
    def __init__(
        self,
        scan_repo: ScanEventRepository,
        card_repo: CardRepository,
        group_repo: AdminCardGroupRepository | None = None,
    ) -> None:
        self.scans = scan_repo
        self.cards = card_repo
        self.groups = group_repo
        self._cache: dict[str, tuple[float, DashboardResponse]] = {}

    async def _acl_for_user(self, user: UserDB | None):
        if user is None or self.groups is None:
            return None
        return await build_acl_filter(user, self.groups)

    async def dashboard(
        self,
        from_dt: datetime,
        to_dt: datetime,
        user: UserDB | None = None,
    ) -> DashboardResponse:
        acl_filter = await self._acl_for_user(user)
        scope_key = "all"
        if user is not None:
            if user.role == UserRole.SUPER_ADMIN:
                scope_key = "super"
            else:
                cats = await self.groups.categories_for_user(user.id) if self.groups else []
                scope_key = f"u:{user.id}:cats:{','.join(str(c) for c in sorted(cats))}"
        cache_key = f"dash:{scope_key}:{from_dt.isoformat()}:{to_dt.isoformat()}"
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached and cached[0] > now:
            return cached[1]

        last_30_from = datetime.now(UTC) - timedelta(days=30)

        total, last30, by_day, top_c, top_d, top_cards, unique, active = await asyncio.gather(
            self.scans.total_scans(from_dt=from_dt, to_dt=to_dt, acl_filter=acl_filter),
            self.scans.total_scans(from_dt=last_30_from, acl_filter=acl_filter),
            self.scans.by_day(from_dt=from_dt, to_dt=to_dt, acl_filter=acl_filter),
            self.scans.top_regions(from_dt=from_dt, to_dt=to_dt, acl_filter=acl_filter),
            self.scans.top_devices(from_dt=from_dt, to_dt=to_dt, acl_filter=acl_filter),
            self.scans.top_cards(from_dt=from_dt, to_dt=to_dt, acl_filter=acl_filter),
            self.scans.unique_cards(from_dt=from_dt, to_dt=to_dt, acl_filter=acl_filter),
            self.scans.unique_cards(
                from_dt=last_30_from, to_dt=datetime.now(UTC), acl_filter=acl_filter
            ),
        )

        result = DashboardResponse(
            kpi=DashboardKpi(
                total_scans=total,
                last_30d_scans=last30,
                unique_cards=unique,
                active_members=active,
            ),
            by_day=[TimelinePoint(**p) for p in by_day],
            top_regions=[
                RegionStats(region=_localize_region(c["region"]) or "—", count=c["count"])
                for c in top_c
            ],
            top_devices=[DeviceStats(**d) for d in top_d],
            top_cards=[TopCard(**t) for t in top_cards],
        )
        self._cache[cache_key] = (now + _CACHE_TTL_SECONDS, result)
        return result

    async def card_analytics(
        self,
        card_id: UUID,
        from_dt: datetime,
        to_dt: datetime,
        user: UserDB | None = None,
    ) -> CardAnalytics:
        if user is not None:
            acl_filter = await self._acl_for_user(user)
            card = await self.cards.get_by_id(card_id, acl_filter=acl_filter)
            if card is None:
                raise NotFoundError()

        total, last_scan, by_day, by_region, by_device = await asyncio.gather(
            self.scans.card_total_scans(card_id, from_dt=from_dt, to_dt=to_dt),
            self.scans.last_scan(card_id),
            self.scans.by_day(from_dt=from_dt, to_dt=to_dt, card_id=card_id),
            self.scans.by_region_for_card(card_id, from_dt=from_dt, to_dt=to_dt),
            self.scans.by_device_for_card(card_id, from_dt=from_dt, to_dt=to_dt),
        )
        return CardAnalytics(
            card_id=card_id,
            total_scans=total,
            last_scan=last_scan,
            by_day=[TimelinePoint(**p) for p in by_day],
            by_region=[
                RegionStats(region=_localize_region(c["region"]) or "—", count=c["count"])
                for c in by_region
            ],
            by_device=[DeviceStats(**d) for d in by_device],
        )

    async def top_active_users(
        self,
        from_dt: datetime,
        to_dt: datetime,
        page: int = 1,
        page_size: int = 10,
        user: UserDB | None = None,
    ) -> TopActiveUsersResponse:
        acl_filter = await self._acl_for_user(user)
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        items_data, total = await asyncio.gather(
            self.scans.top_active_users(
                from_dt=from_dt,
                to_dt=to_dt,
                limit=page_size,
                offset=offset,
                acl_filter=acl_filter,
            ),
            self.scans.top_active_users_count(
                from_dt=from_dt,
                to_dt=to_dt,
                acl_filter=acl_filter,
            ),
        )
        card_ids = [i["card_id"] for i in items_data]
        top_regions, top_devices = await asyncio.gather(
            self.scans.top_region_per_card(card_ids=card_ids, from_dt=from_dt, to_dt=to_dt),
            self.scans.top_device_per_card(card_ids=card_ids, from_dt=from_dt, to_dt=to_dt),
        )
        return TopActiveUsersResponse(
            items=[
                TopActiveUser(
                    **i,
                    top_region=top_regions.get(i["card_id"]),
                    top_device=top_devices.get(i["card_id"]),
                )
                for i in items_data
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
