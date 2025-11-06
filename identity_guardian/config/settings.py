import logging
import os
from typing import Literal, Optional, Union

from azure.identity.aio import AzureCliCredential, ManagedIdentityCredential
from msgraph import GraphServiceClient
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

    azure_tenant_id: str = Field(default="", description="Azure tenant ID for Graph access")
    azure_subscription_id: str = Field(default="", description="Azure subscription ID for resource scope")

    identity_provider: str = Field(default="mock", description="Identity provider (mock, azure)")
    itsm_provider: str = Field(default="mock", description="ITSM provider (mock, servicenow, jira)")
    siem_provider: str = Field(default="mock", description="SIEM provider (mock, splunk, sentinel)")
    grc_provider: str = Field(default="mock", description="GRC provider (mock, archer, servicenow_grc)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


_settings_instance = None

_graph_client: Optional[GraphServiceClient] = None
_graph_credential: Optional[Union[AzureCliCredential, ManagedIdentityCredential]] = None

logger = logging.getLogger(__name__)


RESOURCE_GROUP_MAP = {
    "financial_db": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Finance DB group
    "snowflake_prod": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    # Add more resource to group mappings as needed.
}


PRIVILEGED_RESOURCE_ROLE_MAP = {
    # Example: Global Administrator role definition for tenant-wide scope
    "global_admin": {
        "role_definition_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "directory_scope_id": "/",
        "duration": "PT2H",
    },
    # Extend with additional privileged resources mapped to role definitions.
}


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


async def get_graph_client() -> Optional[GraphServiceClient]:
    """Create or reuse a Microsoft Graph client based on configuration."""
    global _graph_client, _graph_credential

    if os.getenv("IDENTITY_PROVIDER", "mock").lower() != "azure":
        return None

    if _graph_client is not None:
        return _graph_client

    tenant_id = os.getenv("AZURE_TENANT_ID") or get_settings().azure_tenant_id
    auth_mode = os.getenv("AZURE_AUTH_MODE", "azure_cli").lower()

    if auth_mode == "managed_identity":
        client_id = os.getenv("AZURE_CLIENT_ID") or None
        credential = ManagedIdentityCredential(client_id=client_id)
        logger.info("Initialized ManagedIdentityCredential for Microsoft Graph")
    else:
        credential = AzureCliCredential(tenant_id=tenant_id)
        logger.info("Initialized AzureCliCredential for Microsoft Graph")

    scopes = ["https://graph.microsoft.com/.default"]
    _graph_credential = credential
    _graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    return _graph_client


async def close_graph_client() -> None:
    """Dispose the cached Graph credential when shutting down."""
    global _graph_client, _graph_credential

    if _graph_credential is not None:
        await _graph_credential.close()

    _graph_client = None
    _graph_credential = None
