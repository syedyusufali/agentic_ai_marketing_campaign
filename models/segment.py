"""
Segment Models

Defines customer segments and their criteria.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from enum import Enum
import uuid


class SegmentOperator(Enum):
    """Operators for segment criteria"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    IS_SET = "is_set"
    IS_NOT_SET = "is_not_set"
    BETWEEN = "between"


class SegmentLogic(Enum):
    """Logic for combining criteria"""
    AND = "and"
    OR = "or"


@dataclass
class SegmentCriteria:
    """
    A single criterion for segment membership.
    """
    field: str  # Customer attribute to filter on
    operator: SegmentOperator = SegmentOperator.EQUALS
    value: Any = None  # Value(s) to compare against
    value_type: str = "string"  # string, number, date, boolean

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "value_type": self.value_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SegmentCriteria":
        data = data.copy()
        if "operator" in data:
            data["operator"] = SegmentOperator(data["operator"])
        return cls(**data)

    def evaluate(self, customer) -> bool:
        """
        Evaluate if a customer matches this criterion.

        Args:
            customer: CustomerProfile object

        Returns:
            True if customer matches, False otherwise
        """
        # Get the field value from customer
        if hasattr(customer, self.field):
            field_value = getattr(customer, self.field)
        elif hasattr(customer, 'custom_attributes') and self.field in customer.custom_attributes:
            field_value = customer.custom_attributes[self.field]
        else:
            field_value = None

        # Apply operator
        if self.operator == SegmentOperator.EQUALS:
            return field_value == self.value

        elif self.operator == SegmentOperator.NOT_EQUALS:
            return field_value != self.value

        elif self.operator == SegmentOperator.GREATER_THAN:
            return field_value is not None and field_value > self.value

        elif self.operator == SegmentOperator.LESS_THAN:
            return field_value is not None and field_value < self.value

        elif self.operator == SegmentOperator.GREATER_THAN_OR_EQUAL:
            return field_value is not None and field_value >= self.value

        elif self.operator == SegmentOperator.LESS_THAN_OR_EQUAL:
            return field_value is not None and field_value <= self.value

        elif self.operator == SegmentOperator.CONTAINS:
            if isinstance(field_value, str):
                return self.value in field_value
            elif isinstance(field_value, list):
                return self.value in field_value
            return False

        elif self.operator == SegmentOperator.NOT_CONTAINS:
            if isinstance(field_value, str):
                return self.value not in field_value
            elif isinstance(field_value, list):
                return self.value not in field_value
            return True

        elif self.operator == SegmentOperator.IN:
            return field_value in (self.value if isinstance(self.value, list) else [self.value])

        elif self.operator == SegmentOperator.NOT_IN:
            return field_value not in (self.value if isinstance(self.value, list) else [self.value])

        elif self.operator == SegmentOperator.IS_SET:
            return field_value is not None and field_value != ""

        elif self.operator == SegmentOperator.IS_NOT_SET:
            return field_value is None or field_value == ""

        elif self.operator == SegmentOperator.BETWEEN:
            if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                return field_value is not None and self.value[0] <= field_value <= self.value[1]
            return False

        return False


@dataclass
class Segment:
    """
    A customer segment with criteria for membership.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Segment criteria
    criteria: List[Dict[str, Any]] = field(default_factory=list)
    logic: SegmentLogic = SegmentLogic.AND  # How to combine criteria

    # Segment metadata
    customer_count: int = 0
    is_dynamic: bool = True  # Dynamic segments are re-evaluated, static are fixed
    is_ai_generated: bool = False  # Whether created by AI agent

    # Tags for organization
    tags: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_computed_at: Optional[datetime] = None

    def get_criteria_objects(self) -> List[SegmentCriteria]:
        """Convert criteria dicts to SegmentCriteria objects"""
        return [SegmentCriteria.from_dict(c) for c in self.criteria]

    def evaluate_customer(self, customer) -> bool:
        """
        Evaluate if a customer belongs to this segment.

        Args:
            customer: CustomerProfile object

        Returns:
            True if customer matches segment criteria
        """
        criteria_objects = self.get_criteria_objects()

        if not criteria_objects:
            return False

        results = [c.evaluate(customer) for c in criteria_objects]

        if self.logic == SegmentLogic.AND:
            return all(results)
        else:  # OR
            return any(results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "criteria": self.criteria,
            "logic": self.logic.value,
            "customer_count": self.customer_count,
            "is_dynamic": self.is_dynamic,
            "is_ai_generated": self.is_ai_generated,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_computed_at": self.last_computed_at.isoformat() if self.last_computed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Segment":
        data = data.copy()
        if "logic" in data:
            data["logic"] = SegmentLogic(data["logic"])
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if "last_computed_at" in data and data["last_computed_at"]:
            data["last_computed_at"] = datetime.fromisoformat(data["last_computed_at"])
        return cls(**data)

    def add_criterion(
        self,
        field: str,
        operator: Union[SegmentOperator, str],
        value: Any,
        value_type: str = "string"
    ):
        """Add a criterion to the segment"""
        if isinstance(operator, str):
            operator = SegmentOperator(operator)

        criterion = SegmentCriteria(
            field=field,
            operator=operator,
            value=value,
            value_type=value_type
        )
        self.criteria.append(criterion.to_dict())
        self.updated_at = datetime.utcnow()


# Predefined segment templates
SEGMENT_TEMPLATES = {
    "high_value_customers": Segment(
        name="High Value Customers",
        description="Customers with lifetime value score >= 80",
        criteria=[
            {"field": "lifetime_value_score", "operator": "gte", "value": 80, "value_type": "number"}
        ]
    ),
    "at_risk_churners": Segment(
        name="At Risk of Churning",
        description="Customers with high churn risk score",
        criteria=[
            {"field": "churn_risk_score", "operator": "gte", "value": 70, "value_type": "number"}
        ]
    ),
    "new_customers": Segment(
        name="New Customers",
        description="Customers with 0-1 purchases",
        criteria=[
            {"field": "total_purchases", "operator": "lte", "value": 1, "value_type": "number"}
        ]
    ),
    "inactive_30_days": Segment(
        name="Inactive 30+ Days",
        description="Customers who haven't purchased in 30+ days",
        criteria=[
            {"field": "days_since_last_purchase", "operator": "gte", "value": 30, "value_type": "number"}
        ]
    ),
    "highly_engaged": Segment(
        name="Highly Engaged",
        description="Customers with high engagement scores",
        criteria=[
            {"field": "engagement_score", "operator": "gte", "value": 70, "value_type": "number"}
        ]
    ),
    "repeat_buyers": Segment(
        name="Repeat Buyers",
        description="Customers with 3+ purchases",
        criteria=[
            {"field": "total_purchases", "operator": "gte", "value": 3, "value_type": "number"}
        ]
    ),
}
