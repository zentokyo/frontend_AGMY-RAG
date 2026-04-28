from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class PostgresConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, env_prefix="POSTGRES_", extra="ignore")
    host: str
    port: int
    user: str
    password: str
    db: str

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class MinioConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, env_prefix="S3_", extra="ignore")
    host: str
    port: str
    user: str
    password: str
    bucket: str

    @property
    def s3_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class Config(BaseSettings):
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    minio: MinioConfig = Field(default_factory=MinioConfig)


config = Config()
