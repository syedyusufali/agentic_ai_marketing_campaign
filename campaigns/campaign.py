"""
Campaign Model

Defines marketing campaigns and their lifecycle.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import uuid


class CampaignStatus(Enum):
    """Campaign lifecycle status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignType(Enum):
    """Types of campaigns"""
    ONE_TIME = "one_time"  # Single send
    AUTOMATED = "automated"  # Triggered/workflow based
    RECURRING = "recurring"  # Scheduled recurring


@dataclass
class Campaign:
    """
    A marketing campaign targeting customer segments.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Type and status
    campaign_type: CampaignType = CampaignType.ONE_TIME
    status: CampaignStatus = CampaignStatus.DRAFT

    # Targeting
    segment_ids: List[str] = field(default_factory=list)

    # Content
    content: Dict[str, Any] = field(default_factory=dict)
    # Example: {"email": {"subject": "...", "body": "..."}, "sms": {...}}

    # Workflow (for automated campaigns)
    workflow: Dict[str, Any] = field(default_factory=dict)

    # Scheduling
    schedule: Dict[str, Any] = field(default_factory=dict)
    # Example: {"type": "immediate"} or {"type": "scheduled", "datetime": "..."}

    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    # Example: {"sent": 100, "delivered": 98, "opens": 45, "clicks": 12}

    # AI generation info
    is_ai_generated: bool = False
    generation_prompt: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "campaign_type": self.campaign_type.value,
            "status": self.status.value,
            "segment_ids": self.segment_ids,
            "content": self.content,
            "workflow": self.workflow,
            "schedule": self.schedule,
            "metrics": self.metrics,
            "is_ai_generated": self.is_ai_generated,
            "generation_prompt": self.generation_prompt,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        data = data.copy()
        if "campaign_type" in data:
            data["campaign_type"] = CampaignType(data["campaign_type"])
        if "status" in data:
            data["status"] = CampaignStatus(data["status"])
        for field_name in ["created_at", "updated_at", "started_at", "completed_at"]:
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])
        return cls(**data)

    def start(self):
        """Start the campaign"""
        self.status = CampaignStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def pause(self):
        """Pause the campaign"""
        self.status = CampaignStatus.PAUSED
        self.updated_at = datetime.utcnow()

    def resume(self):
        """Resume a paused campaign"""
        self.status = CampaignStatus.RUNNING
        self.updated_at = datetime.utcnow()

    def complete(self):
        """Mark campaign as completed"""
        self.status = CampaignStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def cancel(self):
        """Cancel the campaign"""
        self.status = CampaignStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def update_metrics(self, **kwargs):
        """Update campaign metrics"""
        for key, value in kwargs.items():
            if isinstance(value, (int, float)):
                self.metrics[key] = self.metrics.get(key, 0) + value
            else:
                self.metrics[key] = value
        self.updated_at = datetime.utcnow()

    @property
    def is_active(self) -> bool:
        """Check if campaign is active"""
        return self.status in [CampaignStatus.RUNNING, CampaignStatus.SCHEDULED]

    @property
    def can_start(self) -> bool:
        """Check if campaign can be started"""
        return self.status in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]

    def get_summary(self) -> str:
        """Get campaign summary"""
        metrics_str = ""
        if self.metrics:
            metrics_str = f" | Sent: {self.metrics.get('sent', 0)}, Opens: {self.metrics.get('opens', 0)}"

        return f"{self.name} ({self.status.value}){metrics_str}"


class CampaignBuilder:
    """
    Builder pattern for creating campaigns.
    """

    def __init__(self):
        self._campaign = Campaign()

    def name(self, name: str) -> "CampaignBuilder":
        self._campaign.name = name
        return self

    def description(self, description: str) -> "CampaignBuilder":
        self._campaign.description = description
        return self

    def type(self, campaign_type: CampaignType) -> "CampaignBuilder":
        self._campaign.campaign_type = campaign_type
        return self

    def target_segment(self, segment_id: str) -> "CampaignBuilder":
        self._campaign.segment_ids.append(segment_id)
        return self

    def target_segments(self, segment_ids: List[str]) -> "CampaignBuilder":
        self._campaign.segment_ids.extend(segment_ids)
        return self

    def email_content(
        self,
        subject: str,
        body: str,
        preheader: Optional[str] = None,
        cta_text: Optional[str] = None,
        cta_url: Optional[str] = None
    ) -> "CampaignBuilder":
        self._campaign.content["email"] = {
            "subject": subject,
            "body": body,
            "preheader": preheader,
            "cta_text": cta_text,
            "cta_url": cta_url,
        }
        return self

    def sms_content(self, message: str) -> "CampaignBuilder":
        self._campaign.content["sms"] = {"message": message}
        return self

    def workflow(self, workflow: Dict[str, Any]) -> "CampaignBuilder":
        self._campaign.workflow = workflow
        self._campaign.campaign_type = CampaignType.AUTOMATED
        return self

    def schedule_now(self) -> "CampaignBuilder":
        self._campaign.schedule = {"type": "immediate"}
        return self

    def schedule_at(self, dt: datetime) -> "CampaignBuilder":
        self._campaign.schedule = {
            "type": "scheduled",
            "datetime": dt.isoformat()
        }
        self._campaign.status = CampaignStatus.SCHEDULED
        return self

    def ai_generated(self, prompt: str) -> "CampaignBuilder":
        self._campaign.is_ai_generated = True
        self._campaign.generation_prompt = prompt
        return self

    def build(self) -> Campaign:
        return self._campaign
