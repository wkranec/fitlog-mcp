from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    fitlog_vault_path: Path = Path("./vault")

    model_config = {"env_file": ".env"}


settings = Settings()
