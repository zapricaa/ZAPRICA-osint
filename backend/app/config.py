from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "ZAPRICA"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite+aiosqlite:///./zaprica.db"
    database_url_sync: str = "sqlite:///./zaprica.db"

    # Authentication
    jwt_secret_key: str = "dev-only-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # LLM Configuration
    planner_llm_provider: Optional[str] = None
    planner_llm_api_key: Optional[str] = None
    planner_llm_model: str = "gpt-4o"
    extractor_llm_provider: Optional[str] = None
    extractor_llm_api_key: Optional[str] = None
    extractor_llm_model: str = "gpt-4o-mini"

    # Evidence Storage
    evidence_storage_backend: str = "local"
    evidence_storage_path: str = "./evidence_store"
    s3_bucket_name: Optional[str] = None
    s3_endpoint_url: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Shell Worker
    shell_worker_enabled: bool = False
    shell_worker_timeout_seconds: int = 30
    shell_worker_memory_limit: str = "256m"

    # Browser Worker
    browser_worker_enabled: bool = False
    browser_worker_timeout_seconds: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
