"""
Customer Profile Management

Provides unified customer profiles with 360° view across all touchpoints.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import uuid


class CustomerStatus(Enum):
    """Customer lifecycle status"""
    PROSPECT = "prospect"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    CHURNED = "churned"
    REACTIVATED = "reactivated"


@dataclass
class CustomerProfile:
    """
    Unified customer profile with all attributes and computed traits.
    This is the core entity for the CDP.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Identity
    email: Optional[str] = None
    phone: Optional[str] = None
    external_ids: Dict[str, str] = field(default_factory=dict)  # e.g., {"shopify": "123", "stripe": "cus_xxx"}

    # Demographics
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None

    # Behavioral attributes (computed)
    total_purchases: int = 0
    total_revenue: float = 0.0
    average_order_value: float = 0.0
    purchase_frequency: float = 0.0  # purchases per month
    days_since_last_purchase: Optional[int] = None

    # Engagement metrics
    email_opens: int = 0
    email_clicks: int = 0
    website_visits: int = 0
    last_active: Optional[datetime] = None

    # Predictive scores (0-100)
    churn_risk_score: float = 0.0
    lifetime_value_score: float = 0.0
    engagement_score: float = 0.0
    conversion_probability: float = 0.0

    # Segmentation
    segments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Status
    status: CustomerStatus = CustomerStatus.PROSPECT

    # Custom attributes
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        """Get full name"""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown"

    @property
    def is_high_value(self) -> bool:
        """Check if customer is high value (top 20% LTV)"""
        return self.lifetime_value_score >= 80

    @property
    def is_at_risk(self) -> bool:
        """Check if customer is at risk of churning"""
        return self.churn_risk_score >= 70

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization"""
        return {
            "id": self.id,
            "email": self.email,
            "phone": self.phone,
            "external_ids": self.external_ids,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "age": self.age,
            "gender": self.gender,
            "location": self.location,
            "timezone": self.timezone,
            "total_purchases": self.total_purchases,
            "total_revenue": self.total_revenue,
            "average_order_value": self.average_order_value,
            "purchase_frequency": self.purchase_frequency,
            "days_since_last_purchase": self.days_since_last_purchase,
            "email_opens": self.email_opens,
            "email_clicks": self.email_clicks,
            "website_visits": self.website_visits,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "churn_risk_score": self.churn_risk_score,
            "lifetime_value_score": self.lifetime_value_score,
            "engagement_score": self.engagement_score,
            "conversion_probability": self.conversion_probability,
            "segments": self.segments,
            "tags": self.tags,
            "status": self.status.value,
            "custom_attributes": self.custom_attributes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomerProfile":
        """Create from dictionary"""
        data = data.copy()

        # Handle datetime fields
        if data.get("last_active"):
            data["last_active"] = datetime.fromisoformat(data["last_active"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # Handle enum
        if data.get("status"):
            data["status"] = CustomerStatus(data["status"])

        return cls(**data)


class Customer:
    """
    Customer management class with operations on customer profiles.
    """

    def __init__(self, storage):
        self.storage = storage

    def create(self, **kwargs) -> CustomerProfile:
        """Create a new customer profile"""
        profile = CustomerProfile(**kwargs)
        self.storage.save_customer(profile)
        return profile

    def get(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer by ID"""
        return self.storage.get_customer(customer_id)

    def get_by_email(self, email: str) -> Optional[CustomerProfile]:
        """Get customer by email"""
        return self.storage.get_customer_by_email(email)

    def update(self, customer_id: str, **kwargs) -> Optional[CustomerProfile]:
        """Update customer profile"""
        profile = self.get(customer_id)
        if profile:
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = datetime.utcnow()
            self.storage.save_customer(profile)
        return profile

    def merge(self, primary_id: str, secondary_id: str) -> Optional[CustomerProfile]:
        """Merge two customer profiles (identity resolution)"""
        primary = self.get(primary_id)
        secondary = self.get(secondary_id)

        if not primary or not secondary:
            return None

        # Merge external IDs
        primary.external_ids.update(secondary.external_ids)

        # Merge segments and tags
        primary.segments = list(set(primary.segments + secondary.segments))
        primary.tags = list(set(primary.tags + secondary.tags))

        # Sum behavioral metrics
        primary.total_purchases += secondary.total_purchases
        primary.total_revenue += secondary.total_revenue
        primary.email_opens += secondary.email_opens
        primary.email_clicks += secondary.email_clicks
        primary.website_visits += secondary.website_visits

        # Recalculate averages
        if primary.total_purchases > 0:
            primary.average_order_value = primary.total_revenue / primary.total_purchases

        # Use most recent activity
        if secondary.last_active and (not primary.last_active or secondary.last_active > primary.last_active):
            primary.last_active = secondary.last_active

        # Merge custom attributes
        primary.custom_attributes.update(secondary.custom_attributes)

        # Save merged profile and delete secondary
        primary.updated_at = datetime.utcnow()
        self.storage.save_customer(primary)
        self.storage.delete_customer(secondary_id)

        return primary

    def search(self, **criteria) -> List[CustomerProfile]:
        """Search customers by criteria"""
        return self.storage.search_customers(**criteria)

    def get_segment(self, segment_name: str) -> List[CustomerProfile]:
        """Get all customers in a segment"""
        return self.storage.get_customers_in_segment(segment_name)

    def add_to_segment(self, customer_id: str, segment_name: str):
        """Add customer to a segment"""
        profile = self.get(customer_id)
        if profile and segment_name not in profile.segments:
            profile.segments.append(segment_name)
            profile.updated_at = datetime.utcnow()
            self.storage.save_customer(profile)

    def remove_from_segment(self, customer_id: str, segment_name: str):
        """Remove customer from a segment"""
        profile = self.get(customer_id)
        if profile and segment_name in profile.segments:
            profile.segments.remove(segment_name)
            profile.updated_at = datetime.utcnow()
            self.storage.save_customer(profile)
