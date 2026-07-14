from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from std_cards.logo_presets import is_valid_logo_key


class CategoryCode(StrEnum):
    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"


class CategoryDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: CategoryCode
    name_ru: str
    order_idx: int
    color_hex: str | None


class BackgroundSolid(BaseModel):
    kind: Literal["solid"] = "solid"
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class BackgroundGradient(BaseModel):
    kind: Literal["gradient"] = "gradient"
    from_color: str = Field(alias="from", pattern=r"^#[0-9A-Fa-f]{6}$")
    to_color: str = Field(alias="to", pattern=r"^#[0-9A-Fa-f]{6}$")
    angle: int = Field(ge=0, le=360)
    model_config = ConfigDict(populate_by_name=True)


class CustomField(BaseModel):
    key: str
    label: str
    value: str
    type: Literal["text", "number", "date", "url", "phone", "email"] = "text"
    is_hidden: bool = False
    multiline_label: bool = False


class ContactBlock(BaseModel):
    type: (
        Literal[
            "telegram",
            "whatsapp",
            "instagram",
            "facebook",
            "twitter",
            "youtube",
            "tiktok",
            "snapchat",
            "twitch",
            "discord",
            "linkedin",
            "email",
            "phone",
            "website",
            "vk",
            "ok",
            "max",
            "notes",
        ]
        | None
    ) = None
    value: str = ""
    is_internal: bool = False
    is_hidden: bool = False
    label: str | None = Field(None, max_length=100)
    input_type: Literal["text", "number", "date", "url", "phone", "email"] | None = None


class CardCreate(BaseModel):
    last_name: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    membership_no: str = Field(min_length=1, max_length=50)
    category_id: int | None = None
    template_id: UUID | None = None
    birth_date: date | None = None
    region: str | None = Field(None, max_length=200)
    card_issue_date: date | None = None
    join_date: date | None = None
    chairman: str | None = None
    photo_shape: Literal["square", "circle"] = "square"
    logo_shape: Literal["square", "circle", "rectangle"] = "square"
    bg_kind: Literal["solid", "gradient"] = "solid"
    bg_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    bg_gradient: BackgroundGradient | None = None
    avatar_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    avatar_gradient: BackgroundGradient | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    label_set: list[CustomField] = Field(default_factory=list)
    field_order: list[str] = Field(default_factory=list)
    field_labels: dict[str, str] = Field(default_factory=dict)
    contacts: list[ContactBlock] = Field(default_factory=list)
    internal_blocks: list[ContactBlock] = Field(default_factory=list)
    hide_birth_date: bool = False
    hide_region: bool = False
    hide_card_issue_date: bool = False
    hide_join_date: bool = False
    hide_chairman: bool = False
    feedback_form_enabled: bool = True
    public_slug: str | None = None
    logo_key: str | None = None

    @field_validator("logo_key")
    @classmethod
    def _check_logo_key(cls, v: str | None) -> str | None:
        if not is_valid_logo_key(v):
            raise ValueError(
                "logo_key must be null, 'preset:<id>' for a known preset, or a 'cards/...' S3 key"
            )
        return v


class CardUpdate(BaseModel):
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    membership_no: str | None = None
    category_id: int | None = None
    template_id: UUID | None = None
    birth_date: date | None = None
    region: str | None = None
    card_issue_date: date | None = None
    join_date: date | None = None
    chairman: str | None = None
    photo_shape: Literal["square", "circle"] | None = None
    logo_shape: Literal["square", "circle", "rectangle"] | None = None
    bg_kind: Literal["solid", "gradient"] | None = None
    bg_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    bg_gradient: BackgroundGradient | None = None
    avatar_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    avatar_gradient: BackgroundGradient | None = None
    custom_fields: dict[str, Any] | None = None
    label_set: list[CustomField] | None = None
    field_order: list[str] | None = None
    field_labels: dict[str, str] | None = None
    contacts: list[ContactBlock] | None = None
    internal_blocks: list[ContactBlock] | None = None
    hide_birth_date: bool | None = None
    hide_region: bool | None = None
    hide_card_issue_date: bool | None = None
    hide_join_date: bool | None = None
    hide_chairman: bool | None = None
    feedback_form_enabled: bool | None = None
    is_active: bool | None = None
    assigned_admin_id: UUID | None = None
    logo_key: str | None = None

    @field_validator("logo_key")
    @classmethod
    def _check_logo_key(cls, v: str | None) -> str | None:
        if not is_valid_logo_key(v):
            raise ValueError(
                "logo_key must be null, 'preset:<id>' for a known preset, or a 'cards/...' S3 key"
            )
        return v


class CardDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    public_slug: str
    category_id: int
    template_id: UUID | None
    last_name: str
    first_name: str
    middle_name: str | None
    full_name_search: str
    membership_no: str
    birth_date: date | None
    region: str | None
    card_issue_date: date | None
    join_date: date | None
    chairman: str | None
    photo_key: str | None
    photo_shape: str
    logo_key: str | None
    logo_shape: str = "square"
    bg_kind: str
    bg_color: str | None
    bg_gradient: dict | None
    avatar_color: str | None = None
    avatar_gradient: dict | None = None
    custom_fields: dict
    label_set: list
    field_order: list[str] = Field(default_factory=list)
    field_labels: dict[str, str] = Field(default_factory=dict)
    contacts: list = Field(default_factory=list)
    internal_blocks: list = Field(default_factory=list)
    hide_birth_date: bool = False
    hide_region: bool = False
    hide_card_issue_date: bool = False
    hide_join_date: bool = False
    hide_chairman: bool = False
    feedback_form_enabled: bool
    created_by: UUID | None
    assigned_admin_id: UUID | None
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CardPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_slug: str
    last_name: str
    first_name: str
    middle_name: str | None
    membership_no: str
    region: str | None
    card_issue_date: date | None
    join_date: date | None
    chairman: str | None
    photo_key: str | None
    photo_shape: str
    logo_key: str | None
    logo_shape: str = "square"
    bg_kind: str
    bg_color: str | None
    bg_gradient: dict | None
    avatar_color: str | None = None
    avatar_gradient: dict | None = None
    custom_fields: dict
    label_set: list
    field_order: list[str] = Field(default_factory=list)
    field_labels: dict[str, str] = Field(default_factory=dict)
    contacts: list = Field(default_factory=list)
    internal_blocks: list = Field(default_factory=list)
    hide_birth_date: bool = False
    hide_region: bool = False
    hide_card_issue_date: bool = False
    hide_join_date: bool = False
    hide_chairman: bool = False
    feedback_form_enabled: bool


class CardListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    public_slug: str
    last_name: str
    first_name: str
    middle_name: str | None
    membership_no: str
    category_id: int
    region: str | None
    is_active: bool
    photo_key: str | None
    birth_date: date | None
    bg_kind: str
    bg_color: str | None
    bg_gradient: dict | None
    template_id: UUID | None = None
    created_at: datetime


class CardsList(BaseModel):
    items: list[CardListItem]
    total: int
    page: int
    page_size: int


DateField = Literal["added", "opened", "modified", "created", "issued"]


class CardsListFilter(BaseModel):
    q: str | None = None
    category_id: int | None = None
    region: str | None = None
    date_field: DateField | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_active: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    sort: Literal[
        "created_at",
        "-created_at",
        "last_name",
        "-last_name",
        "updated_at",
        "-updated_at",
        "membership_no",
        "-membership_no",
        "category_id",
        "-category_id",
        "birth_date",
        "-birth_date",
        "region",
        "-region",
    ] = "-created_at"
