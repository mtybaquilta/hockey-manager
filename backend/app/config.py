from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="HM_")
    database_url: str = "postgresql+psycopg://hm:hm@localhost:5432/hockey_manager"


settings = Settings()
