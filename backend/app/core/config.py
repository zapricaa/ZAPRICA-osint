from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: Literal["development", "staging", "production"] = "development"
    PROJECT_NAME: str = "ZAPRICA OSINT"
    API_V1_STR: str = "/v1"
    SECRET_KEY: str = "dev-secret-key-change-in-production-must-be-at-least-32-chars"
    BOOTSTRAP_SECRET: str = "zaprica_bootstrap_superadmin_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./zaprica.db"

    # Evidence Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./data/evidence"
    OBJECT_STORE_ENDPOINT: Optional[str] = "http://localhost:9000"
    OBJECT_STORE_BUCKET: str = "zaprica-evidence"
    OBJECT_STORE_ACCESS_KEY: Optional[str] = "minioadmin"
    OBJECT_STORE_SECRET_KEY: Optional[str] = "minioadmin"
    OBJECT_STORE_REGION: Optional[str] = "us-east-1"

    # AI / LLM Configuration
    LLM_PROVIDER: Literal["mock", "gemini", "openai"] = "mock"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "gemini-3.8-flash"

    # Google Gemini AI Brain
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_MAIN_HEAD_MODEL: str = "gemini-2.0-flash"
    GEMINI_BROWSER_HEAD_MODEL: str = "gemini-2.0-flash-lite"
    GEMINI_TERMINAL_HEAD_MODEL: str = "gemini-2.0-flash-lite"

    # Sandbox / Tool Execution
    ENABLE_TERMINAL_SANDBOX: bool = True
    MAX_BROWSER_TIMEOUT_SECONDS: int = 60
    MAX_TERMINAL_TIMEOUT_SECONDS: int = 30
    MAX_TOOL_OUTPUT_BYTES: int = 10 * 1024 * 1024  # 10 MB limit

    # Safe Startup Mode Flags (Defaults per Safe Application Startup Requirement)
    ZAPRICA_SAFE_MODE: bool = True
    TERMINAL_EXECUTION_ENABLED: bool = False
    TERMINAL_SANDBOX_REQUIRED: bool = True
    BROWSER_SESSION_AUTOSTART: bool = False
    BROWSER_AUTOMATION_ENABLED: bool = False
    AUTO_INVESTIGATION_ENABLED: bool = False
    AUTO_TOOL_INSTALLATION: bool = False

    # Dedicated Environment Settings
    BROWSER_PROFILES_DIR: str = "./data/browser_profiles"
    BROWSER_HEADLESS: bool = False
    DOCKER_SANDBOX_IMAGE: str = "zaprica-sandbox:latest"

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
