"""
Event Tracking System

Captures and manages customer behavioral events across all touchpoints.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import uuid


class EventType(Enum):
    """Standard event types"""
    # E-commerce events
    PAGE_VIEW = "page_view"
    PRODUCT_VIEW = "product_view"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CHECKOUT_START = "checkout_start"
    PURCHASE = "purchase"
    REFUND = "refund"

    # Engagement events
    EMAIL_OPEN = "email_open"
    EMAIL_CLICK = "email_click"
    EMAIL_BOUNCE = "email_bounce"
    EMAIL_UNSUBSCRIBE = "email_unsubscribe"
    SMS_SENT = "sms_sent"
    SMS_CLICK = "sms_click"
    PUSH_RECEIVED = "push_received"
    PUSH_CLICK = "push_click"

    # User events
    SIGNUP = "signup"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_RESET = "password_reset"
    PROFILE_UPDATE = "profile_update"

    # Support events
    SUPPORT_TICKET = "support_ticket"
    FEEDBACK = "feedback"
    REVIEW = "review"

    # Custom
    CUSTOM = "custom"


@dataclass
class Event:
    """
    A single customer event with properties and context.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = ""
    event_type: EventType = EventType.CUSTOM
    event_name: str = ""  # For custom events

    # Event properties
    properties: Dict[str, Any] = field(default_factory=dict)

    # Context
    source: str = ""  # e.g., "web", "mobile", "email", "api"
    campaign_id: Optional[str] = None
    session_id: Optional[str] = None

    # Location context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referrer: Optional[str] = None

    # Timestamps
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "event_type": self.event_type.value,
            "event_name": self.event_name,
            "properties": self.properties,
            "source": self.source,
            "campaign_id": self.campaign_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "referrer": self.referrer,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create from dictionary"""
        data = data.copy()
        if data.get("event_type"):
            data["event_type"] = EventType(data["event_type"])
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class EventTracker:
    """
    Event tracking and querying system.
    """

    def __init__(self, storage):
        self.storage = storage

    def track(
        self,
        customer_id: str,
        event_type: EventType,
        properties: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Event:
        """
        Track a customer event.

        Args:
            customer_id: The customer ID
            event_type: Type of event
            properties: Event properties/metadata
            **kwargs: Additional event attributes

        Returns:
            The created Event
        """
        event = Event(
            customer_id=customer_id,
            event_type=event_type,
            properties=properties or {},
            **kwargs
        )
        self.storage.save_event(event)

        # Update customer profile based on event
        self._update_customer_from_event(event)

        return event

    def track_custom(
        self,
        customer_id: str,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Event:
        """Track a custom named event"""
        return self.track(
            customer_id=customer_id,
            event_type=EventType.CUSTOM,
            event_name=event_name,
            properties=properties,
            **kwargs
        )

    def get_events(
        self,
        customer_id: str,
        event_type: Optional[EventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get events for a customer.

        Args:
            customer_id: The customer ID
            event_type: Filter by event type
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        return self.storage.get_events(
            customer_id=customer_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

    def get_event_count(
        self,
        customer_id: str,
        event_type: EventType,
        days: int = 30
    ) -> int:
        """Get count of events in the last N days"""
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        events = self.get_events(
            customer_id=customer_id,
            event_type=event_type,
            start_date=start_date
        )
        return len(events)

    def get_last_event(
        self,
        customer_id: str,
        event_type: Optional[EventType] = None
    ) -> Optional[Event]:
        """Get the most recent event for a customer"""
        events = self.get_events(customer_id=customer_id, event_type=event_type, limit=1)
        return events[0] if events else None

    def _update_customer_from_event(self, event: Event):
        """Update customer profile based on event"""
        customer = self.storage.get_customer(event.customer_id)
        if not customer:
            return

        # Update last active
        customer.last_active = event.timestamp

        # Update specific metrics based on event type
        if event.event_type == EventType.PURCHASE:
            customer.total_purchases += 1
            revenue = event.properties.get("revenue", 0)
            customer.total_revenue += revenue
            if customer.total_purchases > 0:
                customer.average_order_value = customer.total_revenue / customer.total_purchases
            customer.days_since_last_purchase = 0

        elif event.event_type == EventType.EMAIL_OPEN:
            customer.email_opens += 1

        elif event.event_type == EventType.EMAIL_CLICK:
            customer.email_clicks += 1

        elif event.event_type == EventType.PAGE_VIEW:
            customer.website_visits += 1

        customer.updated_at = datetime.utcnow()
        self.storage.save_customer(customer)

    def aggregate_events(
        self,
        event_type: EventType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day"
    ) -> Dict[str, int]:
        """
        Aggregate events for analytics.

        Args:
            event_type: Type of event to aggregate
            start_date: Start of date range
            end_date: End of date range
            group_by: Grouping period ("hour", "day", "week", "month")

        Returns:
            Dictionary of period -> count
        """
        return self.storage.aggregate_events(
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )
