from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "customer-service-demo-backend"
    litellm_base_url: str = Field(default="http://localhost:4000", alias="LITELLM_BASE_URL")
    litellm_api_key: str = Field(default="test-key", alias="LITELLM_API_KEY")
    litellm_model: str = Field(default="gpt-4o-mini", alias="LITELLM_MODEL")
