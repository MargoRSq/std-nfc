from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="pg_", extra="ignore")

    HOST: str = "localhost"
    PORT: int = 5432
    USER: str = "std_cards"
    PASSWORD: str = "std_cards_dev"
    DB: str = "std_cards"

    POOL_SIZE: int = 10
    POOL_MAX_OVERFLOW: int = 20
    POOL_RECYCLE_SECONDS: int = 1800
    POOL_PRE_PING: bool = True

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"

    @property
    def migrate_url(self) -> str:
        return f"postgresql+psycopg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"


class NatsConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="nats_", extra="ignore")

    URL: str = "nats://localhost:4222"
    CONSUMER_START: bool = True
    REPLIER_START: bool = False
    HANDLE_TIMEOUT: float = 300.0
    REQUEST_REPLY_SUBJECT: list[str] = ["std_cards.req"]


class MinioConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="minio_", extra="ignore")

    ENDPOINT: str = "http://localhost:9000"
    ACCESS_KEY: str = "std_cards_admin"
    SECRET_KEY: str = "std_cards_dev_password"
    BUCKET_CARDS: str = "std-cards-media"
    BUCKET_IMPORTS: str = "std-cards-imports"
    REGION: str = "us-east-1"
    PRESIGN_TTL_SECONDS: int = 300


class AuthConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="jwt_", extra="ignore")

    SECRET: str = "dev-secret-change-in-prod"
    ACCESS_EXPIRE_MINUTES: int = 15
    REFRESH_EXPIRE_DAYS: int = 7
    BCRYPT_COST: int = 12
    TOTP_ISSUER: str = "STD RF"


class RateLimitConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="rl_", extra="ignore")

    PUBLIC_SCAN_PER_MIN: int = 60
    PUBLIC_SCAN_PER_HOUR: int = 600
    LOGIN_PER_MIN: int = 10
    LOGIN_IP_PER_MIN: int = 30
    NOT_FOUND_BURST_THRESHOLD: int = 50
    NOT_FOUND_BURST_WINDOW_SECONDS: int = 300
    NOT_FOUND_BURST_BLOCK_SECONDS: int = 1800


class SeedConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="seed_", extra="ignore")

    SUPER_ADMIN_EMAIL: str = "admin@std-cards.local"
    SUPER_ADMIN_PASSWORD: str = "ChangeMe123!"


class SmtpConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="smtp_", extra="ignore")

    HOST: str = ""
    PORT: int = 465
    USER: str = ""
    PASSWORD: str = ""
    FROM: str = ""
    SSL: bool = True


class SentryConf(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="sentry_", extra="ignore")

    DSN: str = ""
    ENVIRONMENT: str = "dev"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "std-cards"
    CONSUMER_PREFIX: str = "std-cards-consumer"
    ENVIRONMENT: str = "dev"
    DEBUG: bool = False
    LITERAL_BINDS: bool = True
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str | None = None

    FRONTEND_URL: str = "http://localhost:5173"
    PUBLIC_CARD_BASE_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    MAXMIND_PATH: str = "/opt/geoip/GeoLite2-City.mmdb"

    POSTGRES: PostgresConf = Field(default_factory=PostgresConf)
    NATS: NatsConf = Field(default_factory=NatsConf)
    MINIO: MinioConf = Field(default_factory=MinioConf)
    AUTH: AuthConf = Field(default_factory=AuthConf)
    RATE_LIMIT: RateLimitConf = Field(default_factory=RateLimitConf)
    SEED: SeedConf = Field(default_factory=SeedConf)
    SENTRY: SentryConf = Field(default_factory=SentryConf)
    SMTP: SmtpConf = Field(default_factory=SmtpConf)

    @model_validator(mode="after")
    def _prod_secrets_guard(self) -> "Settings":
        if self.ENVIRONMENT != "dev":
            if self.AUTH.SECRET == "dev-secret-change-in-prod":
                raise ValueError("JWT_SECRET must be set in non-dev environment")
            if self.SEED.SUPER_ADMIN_PASSWORD == "ChangeMe123!":
                raise ValueError("SEED_SUPER_ADMIN_PASSWORD must be set in non-dev environment")
            if self.MINIO.SECRET_KEY == "std_cards_dev_password":
                raise ValueError("MINIO_SECRET_KEY must be set in non-dev environment")
        return self

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT == "dev"

    @property
    def effective_db_url(self) -> str:
        return self.DATABASE_URL or self.POSTGRES.url

    @property
    def effective_migrate_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("+asyncpg", "+psycopg")
        return self.POSTGRES.migrate_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
