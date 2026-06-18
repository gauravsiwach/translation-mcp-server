from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

ENV_FILE = ".env"


class Settings(BaseSettings):
    DB_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_AI_PROVIDER: Optional[str] = "openai"
    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    AUTO_CREATE_DB: bool = False
    AUTO_CREATE_DB_DEFAULT_DB: str = "postgres"
    AI_MODEL: Optional[str] = None
    AI_TIMEOUT: int = 30
    OLLAMA_URL: Optional[str] = None
    # File import settings
    SKIP_AI_IF_VALUE_EXISTS: bool = True
    SOURCE_LANGUAGE: str = "en"
    MAX_FILE_SIZE_MB: int = 10
    AI_BATCH_SIZE: int = 10
    # Feedback corrections settings
    FEEDBACK_CORRECTION_LIMIT: int = 10
    # Environment & RBAC
    ENV: str = "development"
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    # Figma integration settings
    FIGMA_ACCESS_TOKEN: Optional[str] = None

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
    }


settings = Settings()

# informational flag used by startup logging (do not log secrets)
ENV_FILE_EXISTS = Path(ENV_FILE).exists()
