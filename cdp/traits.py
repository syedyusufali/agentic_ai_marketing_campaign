"""
Computed Traits Engine

Automatically computes and updates customer attributes based on events and behaviors.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
import math


class TraitType(Enum):
    """Types of computed traits"""
    COUNT = "count"  # Count of events
    SUM = "sum"  # Sum of a property
    AVERAGE = "average"  # Average of a property
    MIN = "min"  # Minimum value
    MAX = "max"  # Maximum value
    FIRST = "first"  # First occurrence
    LAST = "last"  # Last occurrence
    UNIQUE_COUNT = "unique_count"  # Count of unique values
    CUSTOM = "custom"  # Custom computation


@dataclass
class ComputedTrait:
    """
    Definition of a computed trait.
    """
    name: str
    description: str = ""
    trait_type: TraitType = TraitType.COUNT
    event_type: str = ""  # Event type to compute from
    property_name: Optional[str] = None  # Property to aggregate
    time_window_days: Optional[int] = None  # Time window (None = all time)
    condition: Optional[Dict[str, Any]] = None  # Filter condition

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "trait_type": self.trait_type.value,
            "event_type": self.event_type,
            "property_name": self.property_name,
            "time_window_days": self.time_window_days,
            "condition": self.condition,
        }


class TraitEngine:
    """
    Engine for computing and managing customer traits.
    """

    def __init__(self, storage):
        self.storage = storage
        self._trait_definitions: Dict[str, ComputedTrait] = {}
        self._register_default_traits()

    def _register_default_traits(self):
        """Register default computed traits"""
        default_traits = [
            ComputedTrait(
                name="purchase_count_30d",
                description="Number of purchases in last 30 days",
                trait_type=TraitType.COUNT,
                event_type="purchase",
                time_window_days=30
            ),
            ComputedTrait(
                name="revenue_30d",
                description="Total revenue in last 30 days",
                trait_type=TraitType.SUM,
                event_type="purchase",
                property_name="revenue",
                time_window_days=30
            ),
            ComputedTrait(
                name="last_purchase_date",
                description="Date of last purchase",
                trait_type=TraitType.LAST,
                event_type="purchase"
            ),
            ComputedTrait(
                name="email_open_rate_30d",
                description="Email open rate in last 30 days",
                trait_type=TraitType.CUSTOM,
                event_type="email_open",
                time_window_days=30
            ),
            ComputedTrait(
                name="page_views_7d",
                description="Page views in last 7 days",
                trait_type=TraitType.COUNT,
                event_type="page_view",
                time_window_days=7
            ),
            ComputedTrait(
                name="cart_abandonment_count",
                description="Number of cart abandonments",
                trait_type=TraitType.COUNT,
                event_type="add_to_cart",
                time_window_days=30
            ),
        ]

        for trait in default_traits:
            self.register_trait(trait)

    def register_trait(self, trait: ComputedTrait):
        """Register a new computed trait"""
        self._trait_definitions[trait.name] = trait

    def get_trait_definition(self, name: str) -> Optional[ComputedTrait]:
        """Get trait definition by name"""
        return self._trait_definitions.get(name)

    def list_traits(self) -> List[ComputedTrait]:
        """List all registered traits"""
        return list(self._trait_definitions.values())

    def compute_trait(self, customer_id: str, trait_name: str) -> Any:
        """
        Compute a single trait for a customer.

        Args:
            customer_id: The customer ID
            trait_name: Name of the trait to compute

        Returns:
            The computed trait value
        """
        trait = self._trait_definitions.get(trait_name)
        if not trait:
            return None

        # Get events for computation
        start_date = None
        if trait.time_window_days:
            start_date = datetime.utcnow() - timedelta(days=trait.time_window_days)

        events = self.storage.get_events(
            customer_id=customer_id,
            event_type=trait.event_type,
            start_date=start_date
        )

        # Apply condition filter if present
        if trait.condition:
            events = [e for e in events if self._matches_condition(e, trait.condition)]

        # Compute based on trait type
        if trait.trait_type == TraitType.COUNT:
            return len(events)

        elif trait.trait_type == TraitType.SUM:
            return sum(e.properties.get(trait.property_name, 0) for e in events)

        elif trait.trait_type == TraitType.AVERAGE:
            values = [e.properties.get(trait.property_name, 0) for e in events]
            return sum(values) / len(values) if values else 0

        elif trait.trait_type == TraitType.MIN:
            values = [e.properties.get(trait.property_name) for e in events if e.properties.get(trait.property_name) is not None]
            return min(values) if values else None

        elif trait.trait_type == TraitType.MAX:
            values = [e.properties.get(trait.property_name) for e in events if e.properties.get(trait.property_name) is not None]
            return max(values) if values else None

        elif trait.trait_type == TraitType.FIRST:
            if events:
                sorted_events = sorted(events, key=lambda e: e.timestamp)
                return sorted_events[0].timestamp
            return None

        elif trait.trait_type == TraitType.LAST:
            if events:
                sorted_events = sorted(events, key=lambda e: e.timestamp, reverse=True)
                return sorted_events[0].timestamp
            return None

        elif trait.trait_type == TraitType.UNIQUE_COUNT:
            values = [e.properties.get(trait.property_name) for e in events if e.properties.get(trait.property_name) is not None]
            return len(set(values))

        elif trait.trait_type == TraitType.CUSTOM:
            return self._compute_custom_trait(customer_id, trait, events)

        return None

    def _matches_condition(self, event, condition: Dict[str, Any]) -> bool:
        """Check if event matches condition"""
        for key, value in condition.items():
            if event.properties.get(key) != value:
                return False
        return True

    def _compute_custom_trait(self, customer_id: str, trait: ComputedTrait, events: List) -> Any:
        """Compute custom traits"""
        if trait.name == "email_open_rate_30d":
            # Calculate email open rate
            opens = len([e for e in events if e.event_type.value == "email_open"])
            sent_events = self.storage.get_events(
                customer_id=customer_id,
                event_type="email_sent",
                start_date=datetime.utcnow() - timedelta(days=30)
            )
            sent = len(sent_events) if sent_events else 1
            return (opens / sent * 100) if sent > 0 else 0

        return None

    def compute_all_traits(self, customer_id: str) -> Dict[str, Any]:
        """
        Compute all registered traits for a customer.

        Args:
            customer_id: The customer ID

        Returns:
            Dictionary of trait_name -> value
        """
        return {
            name: self.compute_trait(customer_id, name)
            for name in self._trait_definitions.keys()
        }

    def compute_predictive_scores(self, customer_id: str) -> Dict[str, float]:
        """
        Compute predictive scores for a customer.

        Returns scores for:
        - churn_risk_score: Likelihood of churning (0-100)
        - lifetime_value_score: Predicted LTV percentile (0-100)
        - engagement_score: Current engagement level (0-100)
        - conversion_probability: Likelihood of next conversion (0-100)
        """
        customer = self.storage.get_customer(customer_id)
        if not customer:
            return {}

        # Compute engagement score
        engagement_score = self._compute_engagement_score(customer)

        # Compute churn risk
        churn_risk_score = self._compute_churn_risk(customer)

        # Compute LTV score
        ltv_score = self._compute_ltv_score(customer)

        # Compute conversion probability
        conversion_prob = self._compute_conversion_probability(customer)

        return {
            "engagement_score": engagement_score,
            "churn_risk_score": churn_risk_score,
            "lifetime_value_score": ltv_score,
            "conversion_probability": conversion_prob,
        }

    def _compute_engagement_score(self, customer) -> float:
        """Compute engagement score based on recent activity"""
        score = 0.0

        # Email engagement (40% weight)
        if customer.email_opens > 0:
            email_rate = min(customer.email_opens / max(customer.email_opens + 10, 1), 1.0)
            score += email_rate * 40

        # Website engagement (30% weight)
        if customer.website_visits > 0:
            visit_score = min(customer.website_visits / 10, 1.0)
            score += visit_score * 30

        # Purchase engagement (30% weight)
        if customer.total_purchases > 0:
            purchase_score = min(customer.total_purchases / 5, 1.0)
            score += purchase_score * 30

        return min(score, 100)

    def _compute_churn_risk(self, customer) -> float:
        """Compute churn risk based on recency and engagement decay"""
        risk = 0.0

        # Days since last purchase (50% weight)
        if customer.days_since_last_purchase is not None:
            if customer.days_since_last_purchase > 90:
                risk += 50
            elif customer.days_since_last_purchase > 60:
                risk += 35
            elif customer.days_since_last_purchase > 30:
                risk += 20
            else:
                risk += 5

        # Low engagement (30% weight)
        engagement = self._compute_engagement_score(customer)
        risk += (100 - engagement) * 0.3

        # Declining activity (20% weight)
        if customer.last_active:
            days_inactive = (datetime.utcnow() - customer.last_active).days
            if days_inactive > 30:
                risk += 20
            elif days_inactive > 14:
                risk += 10

        return min(risk, 100)

    def _compute_ltv_score(self, customer) -> float:
        """Compute lifetime value score"""
        # Simple LTV based on revenue and purchase frequency
        if customer.total_revenue <= 0:
            return 10  # Base score for non-purchasers

        # Log scale for revenue
        revenue_score = min(math.log10(customer.total_revenue + 1) * 20, 50)

        # Purchase frequency bonus
        freq_score = min(customer.total_purchases * 5, 30)

        # AOV bonus
        if customer.average_order_value > 100:
            aov_score = 20
        elif customer.average_order_value > 50:
            aov_score = 10
        else:
            aov_score = 5

        return min(revenue_score + freq_score + aov_score, 100)

    def _compute_conversion_probability(self, customer) -> float:
        """Compute probability of next conversion"""
        prob = 20  # Base probability

        # Recent engagement boost
        engagement = self._compute_engagement_score(customer)
        prob += engagement * 0.3

        # Previous purchase behavior
        if customer.total_purchases > 0:
            prob += 20

        # Recent activity
        if customer.days_since_last_purchase is not None:
            if customer.days_since_last_purchase < 7:
                prob += 15
            elif customer.days_since_last_purchase < 30:
                prob += 10

        return min(prob, 95)  # Cap at 95%
