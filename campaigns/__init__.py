"""
Campaign Management Module

Handles campaign creation, execution, and tracking.
"""
from .campaign import Campaign, CampaignStatus, CampaignType
from .workflow import Workflow, WorkflowExecutor
from .channels import ChannelAdapter, EmailChannel, SMSChannel, PushChannel
from .executor import CampaignExecutor

__all__ = [
    "Campaign",
    "CampaignStatus",
    "CampaignType",
    "Workflow",
    "WorkflowExecutor",
    "ChannelAdapter",
    "EmailChannel",
    "SMSChannel",
    "PushChannel",
    "CampaignExecutor",
]
