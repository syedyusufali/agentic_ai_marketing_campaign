"""
Segmentation Agent

Autonomously discovers, creates, and manages customer segments.
Uses AI for natural language segment creation and intelligent audience discovery.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import re

from .base_agent import BaseAgent, AgentResponse, AgentStatus
from models.segment import Segment, SegmentCriteria, SegmentOperator, SEGMENT_TEMPLATES


class SegmentationAgent(BaseAgent):
    """
    AI agent for customer segmentation.

    Capabilities:
    - Create segments from natural language descriptions
    - Discover high-value segments automatically
    - Analyze segment health and overlap
    - Generate lookalike audiences
    - Recommend segment optimizations
    """

    def __init__(self, storage, use_ai: bool = True):
        super().__init__(
            storage=storage,
            name="SegmentationAgent",
            description="Creates and manages customer segments using AI",
            use_ai=use_ai
        )

        # Keywords for segment intent detection
        self._segment_keywords = {
            "high_value": ["high value", "top customers", "best customers", "vip", "premium"],
            "churn_risk": ["churning", "at risk", "leaving", "inactive", "dormant", "churn"],
            "new_customers": ["new", "recent", "just joined", "first time", "new customers"],
            "repeat_buyers": ["repeat", "loyal", "returning", "frequent", "regular"],
            "engaged": ["engaged", "active", "participating", "responsive"],
            "winback": ["winback", "win back", "lapsed", "haven't purchased", "inactive"],
        }

    def get_system_prompt(self) -> str:
        return """You are a customer segmentation expert AI. Your job is to create precise, actionable customer segments based on user requests.

When creating segments, output a JSON object with this structure:
{
    "name": "Segment Name",
    "description": "Clear description of who is in this segment",
    "criteria": [
        {
            "field": "customer_attribute",
            "operator": "equals|not_equals|greater_than|less_than|gte|lte|contains|in|between",
            "value": "value or [values]",
            "value_type": "string|number|date|boolean"
        }
    ],
    "logic": "and|or",
    "reasoning": "Why this segment definition makes sense"
}

Available customer fields:
- total_purchases (number): Total number of purchases
- total_revenue (number): Total amount spent
- average_order_value (number): Average order value
- days_since_last_purchase (number): Days since last purchase
- email_opens (number): Number of email opens
- email_clicks (number): Number of email clicks
- website_visits (number): Number of website visits
- churn_risk_score (number 0-100): AI-predicted churn risk
- lifetime_value_score (number 0-100): Predicted lifetime value
- engagement_score (number 0-100): Current engagement level
- status (string): prospect, active, at_risk, churned, reactivated
- location (string): Customer location
- age (number): Customer age

Be specific with criteria. For example:
- "High value customers" → lifetime_value_score >= 80 OR total_revenue >= 1000
- "At risk of churning" → churn_risk_score >= 70 AND days_since_last_purchase >= 30
- "New customers" → total_purchases <= 1
"""

    def get_capabilities(self) -> List[str]:
        return [
            "create_segment",
            "analyze_segment",
            "discover_segments",
            "get_segment_recommendations",
            "compute_lookalike",
        ]

    def can_handle(self, task: str) -> bool:
        """Check if this agent can handle the task"""
        task_lower = task.lower()
        keywords = ["segment", "audience", "customers who", "find customers", "target", "group"]
        return any(kw in task_lower for kw in keywords)

    def execute(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Execute segmentation task.

        Args:
            task: Natural language task description
            context: Optional context with additional parameters

        Returns:
            AgentResponse with segment data
        """
        import time
        start_time = time.time()
        self.status = AgentStatus.THINKING
        context = context or {}

        try:
            # Determine intent
            task_lower = task.lower()

            if "discover" in task_lower or "find segments" in task_lower:
                response = self._discover_segments()
            elif "analyze" in task_lower:
                segment_name = context.get("segment_name") or self._extract_segment_name(task)
                response = self._analyze_segment(segment_name)
            elif "recommend" in task_lower or "suggestion" in task_lower:
                response = self._get_recommendations()
            elif "lookalike" in task_lower:
                segment_name = context.get("segment_name") or self._extract_segment_name(task)
                response = self._create_lookalike(segment_name)
            else:
                # Default: create segment
                response = self._create_segment(task)

            self.status = AgentStatus.COMPLETED
            response.execution_time_ms = (time.time() - start_time) * 1000
            self._log_execution(task, response, context)
            return response

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResponse(
                success=False,
                message=f"Segmentation error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _create_segment(self, description: str) -> AgentResponse:
        """Create a segment from natural language description"""
        self.status = AgentStatus.EXECUTING

        # Try AI first
        ai_response = self._call_ai(
            f"Create a customer segment for: {description}\n\nReturn only the JSON object."
        )

        segment_data = None
        if ai_response:
            segment_data = self._parse_json_response(ai_response)

        # Fallback to rule-based
        if not segment_data:
            segment_data = self._create_segment_rule_based(description)

        if not segment_data:
            return AgentResponse(
                success=False,
                message="Could not create segment from description",
                suggestions=["Try being more specific about customer attributes"]
            )

        # Create segment object
        segment = Segment(
            name=segment_data.get("name", "Custom Segment"),
            description=segment_data.get("description", description),
            criteria=segment_data.get("criteria", []),
            is_ai_generated=bool(ai_response),
        )

        # Compute segment size
        customers = self._evaluate_segment(segment)
        segment.customer_count = len(customers)

        # Save segment
        self.storage.save_segment(segment)

        # Add customers to segment
        for customer in customers:
            if segment.name not in customer.segments:
                customer.segments.append(segment.name)
                self.storage.save_customer(customer)

        return AgentResponse(
            success=True,
            message=f"Created segment '{segment.name}' with {segment.customer_count} customers",
            data={
                "segment": segment.to_dict(),
                "customer_count": segment.customer_count,
            },
            actions_taken=[
                f"Created segment: {segment.name}",
                f"Added {segment.customer_count} customers to segment"
            ],
            reasoning=segment_data.get("reasoning", "Based on provided criteria"),
            confidence=0.9 if ai_response else 0.7
        )

    def _create_segment_rule_based(self, description: str) -> Optional[Dict]:
        """Create segment using rule-based logic"""
        desc_lower = description.lower()

        # Check for known segment types
        for segment_type, keywords in self._segment_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                if segment_type in SEGMENT_TEMPLATES:
                    template = SEGMENT_TEMPLATES[segment_type]
                    return {
                        "name": template.name,
                        "description": template.description,
                        "criteria": template.criteria,
                        "reasoning": f"Matched template: {segment_type}"
                    }

        # Try to extract numeric criteria
        criteria = []

        # Look for purchase patterns
        purchase_match = re.search(r'(\d+)\+?\s*purchases?', desc_lower)
        if purchase_match:
            criteria.append({
                "field": "total_purchases",
                "operator": "gte",
                "value": int(purchase_match.group(1)),
                "value_type": "number"
            })

        # Look for revenue patterns
        revenue_match = re.search(r'\$(\d+)', desc_lower)
        if revenue_match:
            criteria.append({
                "field": "total_revenue",
                "operator": "gte",
                "value": float(revenue_match.group(1)),
                "value_type": "number"
            })

        # Look for days patterns
        days_match = re.search(r'(\d+)\s*days?', desc_lower)
        if days_match and ("haven't" in desc_lower or "inactive" in desc_lower or "since" in desc_lower):
            criteria.append({
                "field": "days_since_last_purchase",
                "operator": "gte",
                "value": int(days_match.group(1)),
                "value_type": "number"
            })

        if criteria:
            return {
                "name": "Custom Segment",
                "description": description,
                "criteria": criteria,
                "reasoning": "Extracted criteria from description"
            }

        return None

    def _evaluate_segment(self, segment: Segment) -> List:
        """Evaluate which customers match segment criteria"""
        all_customers = self.storage.get_all_customers(limit=10000)
        matching = []

        for customer in all_customers:
            if segment.evaluate_customer(customer):
                matching.append(customer)

        return matching

    def _discover_segments(self) -> AgentResponse:
        """Automatically discover high-value segments"""
        self.status = AgentStatus.EXECUTING

        discovered = []
        all_customers = self.storage.get_all_customers(limit=10000)
        total = len(all_customers)

        if total == 0:
            return AgentResponse(
                success=True,
                message="No customers to segment",
                data={"segments": []},
            )

        # Discover based on value distribution
        high_value = [c for c in all_customers if c.lifetime_value_score >= 80]
        if len(high_value) >= 5:
            discovered.append({
                "name": "High Value Customers",
                "count": len(high_value),
                "percentage": round(len(high_value) / total * 100, 1),
                "criteria": [{"field": "lifetime_value_score", "operator": "gte", "value": 80}]
            })

        # Churn risk
        at_risk = [c for c in all_customers if c.churn_risk_score >= 70]
        if len(at_risk) >= 5:
            discovered.append({
                "name": "Churn Risk",
                "count": len(at_risk),
                "percentage": round(len(at_risk) / total * 100, 1),
                "criteria": [{"field": "churn_risk_score", "operator": "gte", "value": 70}]
            })

        # Highly engaged
        engaged = [c for c in all_customers if c.engagement_score >= 70]
        if len(engaged) >= 5:
            discovered.append({
                "name": "Highly Engaged",
                "count": len(engaged),
                "percentage": round(len(engaged) / total * 100, 1),
                "criteria": [{"field": "engagement_score", "operator": "gte", "value": 70}]
            })

        # New customers (0-1 purchases)
        new = [c for c in all_customers if c.total_purchases <= 1]
        if len(new) >= 5:
            discovered.append({
                "name": "New Customers",
                "count": len(new),
                "percentage": round(len(new) / total * 100, 1),
                "criteria": [{"field": "total_purchases", "operator": "lte", "value": 1}]
            })

        # Repeat buyers
        repeat = [c for c in all_customers if c.total_purchases >= 3]
        if len(repeat) >= 5:
            discovered.append({
                "name": "Repeat Buyers",
                "count": len(repeat),
                "percentage": round(len(repeat) / total * 100, 1),
                "criteria": [{"field": "total_purchases", "operator": "gte", "value": 3}]
            })

        return AgentResponse(
            success=True,
            message=f"Discovered {len(discovered)} potential segments",
            data={"segments": discovered, "total_customers": total},
            actions_taken=["Analyzed customer distribution", "Identified natural clusters"],
            suggestions=[
                "Create segments from discovered groups",
                "Analyze overlap between segments",
            ]
        )

    def _analyze_segment(self, segment_name: str) -> AgentResponse:
        """Analyze a segment's health and characteristics"""
        segment = self.storage.get_segment_by_name(segment_name)
        if not segment:
            return AgentResponse(
                success=False,
                message=f"Segment '{segment_name}' not found",
            )

        customers = self.storage.get_customers_in_segment(segment_name)
        if not customers:
            return AgentResponse(
                success=True,
                message=f"Segment '{segment_name}' is empty",
                data={"segment_name": segment_name, "count": 0}
            )

        # Calculate metrics
        total_revenue = sum(c.total_revenue for c in customers)
        avg_ltv = sum(c.lifetime_value_score for c in customers) / len(customers)
        avg_churn_risk = sum(c.churn_risk_score for c in customers) / len(customers)
        avg_engagement = sum(c.engagement_score for c in customers) / len(customers)

        analysis = {
            "segment_name": segment_name,
            "customer_count": len(customers),
            "total_revenue": round(total_revenue, 2),
            "avg_revenue_per_customer": round(total_revenue / len(customers), 2),
            "avg_lifetime_value_score": round(avg_ltv, 1),
            "avg_churn_risk_score": round(avg_churn_risk, 1),
            "avg_engagement_score": round(avg_engagement, 1),
        }

        # Generate insights
        insights = []
        if avg_churn_risk > 60:
            insights.append("High churn risk - consider winback campaign")
        if avg_engagement < 40:
            insights.append("Low engagement - consider re-engagement campaign")
        if avg_ltv > 70:
            insights.append("High value segment - prioritize for VIP treatment")

        return AgentResponse(
            success=True,
            message=f"Analysis of segment '{segment_name}'",
            data=analysis,
            suggestions=insights,
        )

    def _get_recommendations(self) -> AgentResponse:
        """Get segment optimization recommendations"""
        all_segments = self.storage.get_all_segments()
        recommendations = []

        # Check for missing common segments
        segment_names = [s.name.lower() for s in all_segments]

        if not any("high value" in n for n in segment_names):
            recommendations.append({
                "type": "create",
                "suggestion": "Create a 'High Value Customers' segment",
                "reason": "Essential for VIP treatment and retention"
            })

        if not any("churn" in n or "risk" in n for n in segment_names):
            recommendations.append({
                "type": "create",
                "suggestion": "Create an 'At Risk' segment for churn prevention",
                "reason": "Critical for proactive retention"
            })

        if not any("new" in n for n in segment_names):
            recommendations.append({
                "type": "create",
                "suggestion": "Create a 'New Customers' segment",
                "reason": "Important for onboarding campaigns"
            })

        return AgentResponse(
            success=True,
            message=f"Generated {len(recommendations)} recommendations",
            data={"recommendations": recommendations},
        )

    def _create_lookalike(self, segment_name: str) -> AgentResponse:
        """Create a lookalike audience based on a segment"""
        segment = self.storage.get_segment_by_name(segment_name)
        if not segment:
            return AgentResponse(
                success=False,
                message=f"Source segment '{segment_name}' not found"
            )

        source_customers = self.storage.get_customers_in_segment(segment_name)
        if len(source_customers) < 5:
            return AgentResponse(
                success=False,
                message="Source segment too small for lookalike modeling"
            )

        # Calculate average profile
        avg_revenue = sum(c.total_revenue for c in source_customers) / len(source_customers)
        avg_purchases = sum(c.total_purchases for c in source_customers) / len(source_customers)
        avg_engagement = sum(c.engagement_score for c in source_customers) / len(source_customers)

        # Create lookalike criteria with ranges
        lookalike = Segment(
            name=f"Lookalike: {segment_name}",
            description=f"Customers similar to {segment_name}",
            criteria=[
                {
                    "field": "total_revenue",
                    "operator": "between",
                    "value": [avg_revenue * 0.7, avg_revenue * 1.3],
                    "value_type": "number"
                },
                {
                    "field": "engagement_score",
                    "operator": "gte",
                    "value": avg_engagement * 0.8,
                    "value_type": "number"
                }
            ],
            is_ai_generated=True,
        )

        # Evaluate and exclude source segment
        all_customers = self.storage.get_all_customers(limit=10000)
        source_ids = {c.id for c in source_customers}
        lookalike_customers = [
            c for c in all_customers
            if c.id not in source_ids and lookalike.evaluate_customer(c)
        ]

        lookalike.customer_count = len(lookalike_customers)
        self.storage.save_segment(lookalike)

        return AgentResponse(
            success=True,
            message=f"Created lookalike segment with {lookalike.customer_count} customers",
            data={
                "segment": lookalike.to_dict(),
                "source_segment": segment_name,
                "expansion_rate": round(lookalike.customer_count / len(source_customers), 2)
            }
        )

    def _extract_segment_name(self, text: str) -> Optional[str]:
        """Extract segment name from text"""
        # Look for quoted strings
        match = re.search(r'["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)
        return None

    def list_segments(self) -> List[Dict]:
        """List all segments"""
        segments = self.storage.get_all_segments()
        return [s.to_dict() for s in segments]

    def get_segment(self, name: str) -> Optional[Segment]:
        """Get segment by name"""
        return self.storage.get_segment_by_name(name)
