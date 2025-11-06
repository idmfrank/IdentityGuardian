import os
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model to use")
    
    azure_openai_endpoint: str = Field(default="", description="Azure OpenAI endpoint")
    azure_openai_api_key: str = Field(default="", description="Azure OpenAI API key")
    azure_openai_deployment: str = Field(default="", description="Azure OpenAI deployment name")
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    framework_env: Literal["development", "staging", "production"] = Field(default="development")
    
    identity_provider: str = Field(default="mock", description="Identity provider (mock, azure_ad, okta)")
    itsm_provider: str = Field(default="mock", description="ITSM provider (mock, servicenow, jira)")
    siem_provider: str = Field(default="mock", description="SIEM provider (mock, splunk, sentinel)")
    grc_provider: str = Field(default="mock", description="GRC provider (mock, archer, servicenow_grc)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


_settings_instance = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
