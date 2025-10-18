"""Application configuration powered by environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised settings object so services can access external credentials."""

    auth0_domain: Optional[str] = Field(default=None, description="Auth0 tenant domain for auth flows.")
    auth0_client_id: Optional[str] = Field(
        default=None,
        description="Auth0 application identifier used by the frontend.",
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key leveraged for adversarial planning.",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model identifier used when generating AI insights.",
    )
    github_token: Optional[str] = Field(
        default=None,
        description="Optional GitHub personal access token used when fetching repositories.",
    )
    snowflake_account: Optional[str] = Field(
        default=None,
        description="Snowflake account locator when integrating with the real warehouse.",
    )
    use_gemini: bool = Field(
        default=False,
        description="Toggle to enable real Gemini integration when credentials are available.",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_prefix="COGNITOFORGE_",
        extra="allow",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance so every import shares the same configuration."""

    return Settings()
