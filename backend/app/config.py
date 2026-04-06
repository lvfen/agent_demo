from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "customer-service-demo-backend"
    litellm_base_url: str = "http://localhost:4000"
    litellm_api_key: str = "test-key"
    litellm_model: str = "gpt-4o-mini"
