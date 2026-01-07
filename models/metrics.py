"""
Metrics Models

Defines analytics and performance metrics for campaigns and segments.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


@dataclass
class SegmentMetrics:
    """
    Metrics for a customer segment.
    """
    segment_id: str = ""
    segment_name: str = ""

    # Size metrics
    customer_count: int = 0
    percentage_of_total: float = 0.0

    # Value metrics
    total_revenue: float = 0.0
    average_revenue_per_customer: float = 0.0
    average_order_value: float = 0.0

    # Engagement metrics
    average_engagement_score: float = 0.0
    average_email_open_rate: float = 0.0
    average_email_click_rate: float = 0.0

    # Risk metrics
    average_churn_risk: float = 0.0
    high_risk_count: int = 0  # Customers with churn_risk > 70

    # Growth metrics
    growth_rate_30d: float = 0.0  # % change in last 30 days
    new_customers_30d: int = 0

    # Computed at
    computed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "segment_name": self.segment_name,
            "customer_count": self.customer_count,
            "percentage_of_total": round(self.percentage_of_total, 2),
            "total_revenue": round(self.total_revenue, 2),
            "average_revenue_per_customer": round(self.average_revenue_per_customer, 2),
            "average_order_value": round(self.average_order_value, 2),
            "average_engagement_score": round(self.average_engagement_score, 2),
            "average_email_open_rate": round(self.average_email_open_rate, 2),
            "average_email_click_rate": round(self.average_email_click_rate, 2),
            "average_churn_risk": round(self.average_churn_risk, 2),
            "high_risk_count": self.high_risk_count,
            "growth_rate_30d": round(self.growth_rate_30d, 2),
            "new_customers_30d": self.new_customers_30d,
            "computed_at": self.computed_at.isoformat(),
        }


@dataclass
class CampaignMetrics:
    """
    Performance metrics for a marketing campaign.
    """
    campaign_id: str = ""
    campaign_name: str = ""

    # Delivery metrics
    total_targeted: int = 0
    total_sent: int = 0
    total_delivered: int = 0
    total_bounced: int = 0
    total_failed: int = 0

    # Engagement metrics
    total_opens: int = 0
    unique_opens: int = 0
    total_clicks: int = 0
    unique_clicks: int = 0
    total_unsubscribes: int = 0

    # Conversion metrics
    total_conversions: int = 0
    total_revenue: float = 0.0

    # Calculated rates
    @property
    def delivery_rate(self) -> float:
        return (self.total_delivered / self.total_sent * 100) if self.total_sent > 0 else 0

    @property
    def bounce_rate(self) -> float:
        return (self.total_bounced / self.total_sent * 100) if self.total_sent > 0 else 0

    @property
    def open_rate(self) -> float:
        return (self.unique_opens / self.total_delivered * 100) if self.total_delivered > 0 else 0

    @property
    def click_rate(self) -> float:
        return (self.unique_clicks / self.total_delivered * 100) if self.total_delivered > 0 else 0

    @property
    def click_to_open_rate(self) -> float:
        return (self.unique_clicks / self.unique_opens * 100) if self.unique_opens > 0 else 0

    @property
    def conversion_rate(self) -> float:
        return (self.total_conversions / self.total_delivered * 100) if self.total_delivered > 0 else 0

    @property
    def unsubscribe_rate(self) -> float:
        return (self.total_unsubscribes / self.total_delivered * 100) if self.total_delivered > 0 else 0

    @property
    def revenue_per_email(self) -> float:
        return self.total_revenue / self.total_sent if self.total_sent > 0 else 0

    @property
    def average_order_value(self) -> float:
        return self.total_revenue / self.total_conversions if self.total_conversions > 0 else 0

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    computed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "delivery": {
                "total_targeted": self.total_targeted,
                "total_sent": self.total_sent,
                "total_delivered": self.total_delivered,
                "total_bounced": self.total_bounced,
                "total_failed": self.total_failed,
                "delivery_rate": round(self.delivery_rate, 2),
                "bounce_rate": round(self.bounce_rate, 2),
            },
            "engagement": {
                "total_opens": self.total_opens,
                "unique_opens": self.unique_opens,
                "total_clicks": self.total_clicks,
                "unique_clicks": self.unique_clicks,
                "total_unsubscribes": self.total_unsubscribes,
                "open_rate": round(self.open_rate, 2),
                "click_rate": round(self.click_rate, 2),
                "click_to_open_rate": round(self.click_to_open_rate, 2),
                "unsubscribe_rate": round(self.unsubscribe_rate, 2),
            },
            "conversions": {
                "total_conversions": self.total_conversions,
                "total_revenue": round(self.total_revenue, 2),
                "conversion_rate": round(self.conversion_rate, 2),
                "revenue_per_email": round(self.revenue_per_email, 2),
                "average_order_value": round(self.average_order_value, 2),
            },
            "timing": {
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            },
            "computed_at": self.computed_at.isoformat(),
        }

    def get_summary(self) -> str:
        """Get a human-readable summary of campaign performance"""
        return f"""Campaign: {self.campaign_name}
Sent: {self.total_sent:,} | Delivered: {self.total_delivered:,} ({self.delivery_rate:.1f}%)
Opens: {self.unique_opens:,} ({self.open_rate:.1f}%) | Clicks: {self.unique_clicks:,} ({self.click_rate:.1f}%)
Conversions: {self.total_conversions:,} ({self.conversion_rate:.1f}%) | Revenue: ${self.total_revenue:,.2f}"""


@dataclass
class PlatformMetrics:
    """
    Overall platform metrics and KPIs.
    """
    # Customer metrics
    total_customers: int = 0
    active_customers_30d: int = 0
    new_customers_30d: int = 0
    churned_customers_30d: int = 0

    # Revenue metrics
    total_revenue: float = 0.0
    revenue_30d: float = 0.0
    average_customer_value: float = 0.0

    # Engagement metrics
    average_engagement_score: float = 0.0
    average_email_open_rate: float = 0.0
    average_email_click_rate: float = 0.0

    # Campaign metrics
    total_campaigns: int = 0
    active_campaigns: int = 0
    campaigns_30d: int = 0

    # Segment metrics
    total_segments: int = 0
    ai_generated_segments: int = 0

    # Health indicators
    churn_rate_30d: float = 0.0
    customer_health_score: float = 0.0  # 0-100

    computed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customers": {
                "total": self.total_customers,
                "active_30d": self.active_customers_30d,
                "new_30d": self.new_customers_30d,
                "churned_30d": self.churned_customers_30d,
                "churn_rate_30d": round(self.churn_rate_30d, 2),
            },
            "revenue": {
                "total": round(self.total_revenue, 2),
                "last_30d": round(self.revenue_30d, 2),
                "average_customer_value": round(self.average_customer_value, 2),
            },
            "engagement": {
                "average_score": round(self.average_engagement_score, 2),
                "email_open_rate": round(self.average_email_open_rate, 2),
                "email_click_rate": round(self.average_email_click_rate, 2),
            },
            "campaigns": {
                "total": self.total_campaigns,
                "active": self.active_campaigns,
                "last_30d": self.campaigns_30d,
            },
            "segments": {
                "total": self.total_segments,
                "ai_generated": self.ai_generated_segments,
            },
            "health": {
                "score": round(self.customer_health_score, 2),
            },
            "computed_at": self.computed_at.isoformat(),
        }


class MetricsBenchmark:
    """
    Industry benchmarks for comparison.
    """
    # Email benchmarks (industry averages)
    EMAIL_OPEN_RATE_GOOD = 20.0
    EMAIL_OPEN_RATE_EXCELLENT = 30.0
    EMAIL_CLICK_RATE_GOOD = 2.5
    EMAIL_CLICK_RATE_EXCELLENT = 5.0
    EMAIL_CONVERSION_RATE_GOOD = 2.0
    EMAIL_CONVERSION_RATE_EXCELLENT = 5.0

    # Churn benchmarks
    MONTHLY_CHURN_RATE_GOOD = 5.0
    MONTHLY_CHURN_RATE_EXCELLENT = 2.0

    # Engagement benchmarks
    ENGAGEMENT_SCORE_GOOD = 50.0
    ENGAGEMENT_SCORE_EXCELLENT = 75.0

    @classmethod
    def evaluate_email_performance(cls, metrics: CampaignMetrics) -> Dict[str, str]:
        """Evaluate email performance against benchmarks"""
        evaluations = {}

        # Open rate
        if metrics.open_rate >= cls.EMAIL_OPEN_RATE_EXCELLENT:
            evaluations["open_rate"] = "excellent"
        elif metrics.open_rate >= cls.EMAIL_OPEN_RATE_GOOD:
            evaluations["open_rate"] = "good"
        else:
            evaluations["open_rate"] = "needs_improvement"

        # Click rate
        if metrics.click_rate >= cls.EMAIL_CLICK_RATE_EXCELLENT:
            evaluations["click_rate"] = "excellent"
        elif metrics.click_rate >= cls.EMAIL_CLICK_RATE_GOOD:
            evaluations["click_rate"] = "good"
        else:
            evaluations["click_rate"] = "needs_improvement"

        # Conversion rate
        if metrics.conversion_rate >= cls.EMAIL_CONVERSION_RATE_EXCELLENT:
            evaluations["conversion_rate"] = "excellent"
        elif metrics.conversion_rate >= cls.EMAIL_CONVERSION_RATE_GOOD:
            evaluations["conversion_rate"] = "good"
        else:
            evaluations["conversion_rate"] = "needs_improvement"

        return evaluations
