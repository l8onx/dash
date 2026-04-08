from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    PORT: int = 3000
    DATA_DIR: str = "/data"
    DASH_URL: str = "http://localhost:3000"
    DASH_PSK: str = ""  # empty = auth disabled


settings = Settings()
