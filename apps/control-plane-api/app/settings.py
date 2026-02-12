from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    cors_origins: str = Field(default="http://127.0.0.1:3000", alias="CORS_ORIGINS")

    class Config:
        env_file = ".env"

settings = Settings()
