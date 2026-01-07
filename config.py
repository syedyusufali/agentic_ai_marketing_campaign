"""
Configuration management for Agentic AI Marketing Campaign Planner
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class AIConfig:
    """AI provider configuration"""
    provider: str = "anthropic"  # "anthropic" or "openai"
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Fallback to rule-based if no API key
    use_fallback: bool = True


@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "data/marketing_platform.db"


@dataclass
class CampaignConfig:
    """Campaign execution configuration"""
    max_batch_size: int = 1000
    default_timezone: str = "UTC"
    retry_attempts: int = 3


@dataclass
class Config:
    """Main configuration class"""
    ai: AIConfig = field(default_factory=AIConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    campaign: CampaignConfig = field(default_factory=CampaignConfig)

    # App settings
    app_name: str = "Agentic AI Marketing Platform"
    version: str = "1.0.0"
    debug: bool = False

    def __post_init__(self):
        # Ensure data directory exists
        data_dir = Path(self.database.db_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance"""
    return config


def update_config(**kwargs):
    """Update configuration values"""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        elif hasattr(config.ai, key):
            setattr(config.ai, key, value)
        elif hasattr(config.database, key):
            setattr(config.database, key, value)
        elif hasattr(config.campaign, key):
            setattr(config.campaign, key, value)
