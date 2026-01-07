"""
Analytics Agent

Provides insights, predictions, and recommendations based on customer and campaign data.
Uses AI for intelligent analysis and next best action recommendations.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json

from .base_agent import BaseAgent, AgentResponse, AgentStatus
from models.metrics import CampaignMetrics, SegmentMetrics, PlatformMetrics, MetricsBenchmark


class AnalyticsAgent(BaseAgent):
    """
    AI agent for analytics and predictions.

    Capabilities:
    - Analyze campaign performance
    - Predict customer churn
    - Calculate optimal send times
    - Recommend next best actions
    - Generate insights and reports
    """

    def __init__(self, storage, use_ai: bool = True):
        super().__init__(
            storage=storage,
            name="AnalyticsAgent",
            description="Provides analytics, predictions, and insights using AI",
            use_ai=use_ai
        )

    def get_system_prompt(self) -> str:
        return """You are a marketing analytics expert AI. You analyze data and provide actionable insights.

When analyzing data, consider:
- Trends and patterns
- Anomalies and outliers
- Comparative benchmarks
- Root causes
- Actionable recommendations

Output format:
{
    "summary": "Brief summary of findings",
    "insights": [
        {
            "type": "trend|anomaly|opportunity|risk",
            "finding": "What was discovered",
            "impact": "Business impact",
            "recommendation": "What to do about it"
        }
    ],
    "metrics": {
        "key_metric_name": value
    },
    "next_steps": ["List of recommended actions"]
}

Industry benchmarks:
- Email open rate: 20% is good, 30%+ is excellent
- Email click rate: 2.5% is good, 5%+ is excellent
- Conversion rate: 2% is good, 5%+ is excellent
- Monthly churn: <5% is good, <2% is excellent
"""

    def get_capabilities(self) -> List[str]:
        return [
            "analyze_campaign",
            "analyze_segment",
            "predict_churn",
            "get_platform_health",
            "recommend_actions",
            "calculate_optimal_send_time",
        ]

    def can_handle(self, task: str) -> bool:
        task_lower = task.lower()
        keywords = ["analyze", "insight", "report", "predict", "performance", "metrics",
                   "churn", "analytics", "dashboard", "health", "statistics"]
        return any(kw in task_lower for kw in keywords)

    def execute(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """Execute analytics task"""
        import time
        start_time = time.time()
        self.status = AgentStatus.THINKING
        context = context or {}

        try:
            task_lower = task.lower()

            if "campaign" in task_lower:
                campaign_id = context.get("campaign_id")
                response = self._analyze_campaign(campaign_id)
            elif "segment" in task_lower:
                segment_name = context.get("segment_name")
                response = self._analyze_segment(segment_name)
            elif "churn" in task_lower:
                response = self._predict_churn()
            elif "health" in task_lower or "dashboard" in task_lower or "overview" in task_lower:
                response = self._get_platform_health()
            elif "send time" in task_lower or "optimal time" in task_lower:
                response = self._calculate_optimal_send_time()
            elif "recommend" in task_lower or "suggest" in task_lower:
                response = self._recommend_actions()
            else:
                # Default: platform overview
                response = self._get_platform_health()

            self.status = AgentStatus.COMPLETED
            response.execution_time_ms = (time.time() - start_time) * 1000
            self._log_execution(task, response, context)
            return response

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResponse(
                success=False,
                message=f"Analytics error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _get_platform_health(self) -> AgentResponse:
        """Get overall platform health and metrics"""
        self.status = AgentStatus.EXECUTING

        stats = self.storage.get_stats()
        all_customers = self.storage.get_all_customers(limit=10000)

        # Calculate aggregates
        total_revenue = sum(c.total_revenue for c in all_customers)
        avg_engagement = sum(c.engagement_score for c in all_customers) / len(all_customers) if all_customers else 0
        avg_churn_risk = sum(c.churn_risk_score for c in all_customers) / len(all_customers) if all_customers else 0

        # Count risk levels
        high_risk_count = sum(1 for c in all_customers if c.churn_risk_score >= 70)
        low_engagement_count = sum(1 for c in all_customers if c.engagement_score < 30)

        metrics = PlatformMetrics(
            total_customers=stats.get("total_customers", 0),
            total_revenue=total_revenue,
            average_engagement_score=avg_engagement,
            total_campaigns=stats.get("total_campaigns", 0),
            total_segments=stats.get("total_segments", 0),
        )

        # Calculate health score (0-100)
        health_score = 50  # Base
        if avg_engagement >= 50:
            health_score += 15
        if avg_churn_risk < 50:
            health_score += 15
        if high_risk_count / len(all_customers) < 0.2 if all_customers else True:
            health_score += 10
        if stats.get("total_segments", 0) >= 3:
            health_score += 10

        metrics.customer_health_score = health_score

        # Generate insights
        insights = []
        if avg_churn_risk > 50:
            insights.append({
                "type": "risk",
                "finding": f"Average churn risk is {avg_churn_risk:.1f}% - above healthy threshold",
                "impact": "Potential revenue loss from churning customers",
                "recommendation": "Launch win-back campaigns for at-risk segments"
            })

        if high_risk_count > 0:
            insights.append({
                "type": "opportunity",
                "finding": f"{high_risk_count} customers are at high risk of churning",
                "impact": f"Potential loss of {high_risk_count} customers",
                "recommendation": "Create targeted retention campaigns"
            })

        if avg_engagement < 40:
            insights.append({
                "type": "risk",
                "finding": f"Average engagement score is low ({avg_engagement:.1f}%)",
                "impact": "Lower campaign effectiveness",
                "recommendation": "Improve content personalization and relevance"
            })

        if low_engagement_count > 0:
            insights.append({
                "type": "opportunity",
                "finding": f"{low_engagement_count} customers have low engagement",
                "impact": "Untapped potential",
                "recommendation": "Run re-engagement campaigns"
            })

        return AgentResponse(
            success=True,
            message="Platform health analysis complete",
            data={
                "metrics": metrics.to_dict(),
                "insights": insights,
                "summary": f"Platform health score: {health_score}/100"
            },
            suggestions=[
                "Review high-risk customer segment",
                "Optimize campaign targeting",
            ]
        )

    def _analyze_campaign(self, campaign_id: Optional[str]) -> AgentResponse:
        """Analyze campaign performance"""
        self.status = AgentStatus.EXECUTING

        if campaign_id:
            campaign = self.storage.get_campaign(campaign_id)
            if not campaign:
                return AgentResponse(
                    success=False,
                    message=f"Campaign '{campaign_id}' not found"
                )
            campaigns = [campaign]
        else:
            campaigns = self.storage.get_all_campaigns()

        if not campaigns:
            return AgentResponse(
                success=True,
                message="No campaigns to analyze",
                data={"campaigns": []}
            )

        analyses = []
        for campaign in campaigns:
            # Create sample metrics (in real system, would pull from executions)
            metrics = CampaignMetrics(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                total_targeted=campaign.metrics.get("targeted", 0),
                total_sent=campaign.metrics.get("sent", 0),
                total_delivered=campaign.metrics.get("delivered", 0),
                unique_opens=campaign.metrics.get("opens", 0),
                unique_clicks=campaign.metrics.get("clicks", 0),
                total_conversions=campaign.metrics.get("conversions", 0),
                total_revenue=campaign.metrics.get("revenue", 0),
            )

            # Evaluate against benchmarks
            evaluation = MetricsBenchmark.evaluate_email_performance(metrics)

            analyses.append({
                "campaign": campaign.name,
                "metrics": metrics.to_dict(),
                "evaluation": evaluation,
                "summary": metrics.get_summary() if metrics.total_sent > 0 else "No data yet"
            })

        return AgentResponse(
            success=True,
            message=f"Analyzed {len(analyses)} campaign(s)",
            data={"analyses": analyses}
        )

    def _analyze_segment(self, segment_name: Optional[str]) -> AgentResponse:
        """Analyze segment performance"""
        self.status = AgentStatus.EXECUTING

        if segment_name:
            segment = self.storage.get_segment_by_name(segment_name)
            if not segment:
                return AgentResponse(
                    success=False,
                    message=f"Segment '{segment_name}' not found"
                )
            segments = [segment]
        else:
            segments = self.storage.get_all_segments()

        if not segments:
            return AgentResponse(
                success=True,
                message="No segments to analyze",
                data={"segments": []}
            )

        total_customers = self.storage.count_customers()
        analyses = []

        for segment in segments:
            customers = self.storage.get_customers_in_segment(segment.name)
            if not customers:
                continue

            total_revenue = sum(c.total_revenue for c in customers)
            avg_engagement = sum(c.engagement_score for c in customers) / len(customers)
            avg_churn_risk = sum(c.churn_risk_score for c in customers) / len(customers)
            avg_ltv = sum(c.lifetime_value_score for c in customers) / len(customers)

            metrics = SegmentMetrics(
                segment_id=segment.id,
                segment_name=segment.name,
                customer_count=len(customers),
                percentage_of_total=len(customers) / total_customers * 100 if total_customers > 0 else 0,
                total_revenue=total_revenue,
                average_revenue_per_customer=total_revenue / len(customers),
                average_engagement_score=avg_engagement,
                average_churn_risk=avg_churn_risk,
                high_risk_count=sum(1 for c in customers if c.churn_risk_score >= 70),
            )

            # Generate segment-specific insights
            insights = []
            if avg_churn_risk > 60:
                insights.append("High churn risk - prioritize retention")
            if avg_engagement > 70:
                insights.append("High engagement - good for upselling")
            if avg_ltv > 70:
                insights.append("High value - VIP treatment recommended")

            analyses.append({
                "segment": segment.name,
                "metrics": metrics.to_dict(),
                "insights": insights,
            })

        return AgentResponse(
            success=True,
            message=f"Analyzed {len(analyses)} segment(s)",
            data={"analyses": analyses}
        )

    def _predict_churn(self) -> AgentResponse:
        """Predict and analyze customer churn"""
        self.status = AgentStatus.EXECUTING

        all_customers = self.storage.get_all_customers(limit=10000)
        if not all_customers:
            return AgentResponse(
                success=True,
                message="No customers to analyze",
                data={}
            )

        # Categorize by churn risk
        high_risk = [c for c in all_customers if c.churn_risk_score >= 70]
        medium_risk = [c for c in all_customers if 40 <= c.churn_risk_score < 70]
        low_risk = [c for c in all_customers if c.churn_risk_score < 40]

        # Calculate potential revenue at risk
        revenue_at_risk = sum(c.total_revenue * 0.5 for c in high_risk)  # Estimated annual value

        # Common characteristics of high-risk customers
        characteristics = []
        if high_risk:
            avg_days_inactive = sum(c.days_since_last_purchase or 0 for c in high_risk) / len(high_risk)
            avg_engagement = sum(c.engagement_score for c in high_risk) / len(high_risk)

            if avg_days_inactive > 30:
                characteristics.append(f"Average {avg_days_inactive:.0f} days since last purchase")
            if avg_engagement < 30:
                characteristics.append(f"Low engagement (avg {avg_engagement:.1f}%)")

        insights = []
        if len(high_risk) > 0:
            insights.append({
                "type": "risk",
                "finding": f"{len(high_risk)} customers at high risk of churning",
                "impact": f"${revenue_at_risk:,.0f} potential revenue at risk",
                "recommendation": "Implement immediate retention campaign"
            })

        if medium_risk:
            insights.append({
                "type": "opportunity",
                "finding": f"{len(medium_risk)} customers in medium risk zone",
                "impact": "Can be converted to loyal customers with intervention",
                "recommendation": "Proactive engagement campaign recommended"
            })

        return AgentResponse(
            success=True,
            message="Churn prediction analysis complete",
            data={
                "distribution": {
                    "high_risk": len(high_risk),
                    "medium_risk": len(medium_risk),
                    "low_risk": len(low_risk),
                },
                "revenue_at_risk": round(revenue_at_risk, 2),
                "high_risk_characteristics": characteristics,
                "insights": insights,
            },
            suggestions=[
                "Create segment for high-risk customers",
                "Design win-back campaign",
                "Analyze common factors in churned customers",
            ]
        )

    def _calculate_optimal_send_time(self) -> AgentResponse:
        """Calculate optimal send times for campaigns"""
        self.status = AgentStatus.EXECUTING

        # In a real system, this would analyze historical open/click data
        # For now, we return best practices with sample data

        optimal_times = {
            "email": {
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "best_hours": ["10:00 AM", "2:00 PM"],
                "avoid": ["Weekends", "Mondays", "Friday afternoons"],
                "reasoning": "Based on industry benchmarks and typical work patterns"
            },
            "sms": {
                "best_days": ["Tuesday", "Wednesday"],
                "best_hours": ["11:00 AM", "3:00 PM"],
                "avoid": ["Early morning", "Late evening", "Weekends"],
                "reasoning": "SMS requires immediate attention, mid-day is optimal"
            },
            "push": {
                "best_days": ["Any weekday"],
                "best_hours": ["8:00 AM", "12:00 PM", "6:00 PM"],
                "avoid": ["Late night", "Early morning"],
                "reasoning": "Push should align with app usage patterns"
            }
        }

        # Generate segment-specific recommendations
        segment_recommendations = [
            {
                "segment": "High Value Customers",
                "recommendation": "Send during business hours for professional audience",
                "best_time": "Tuesday 10:00 AM"
            },
            {
                "segment": "New Customers",
                "recommendation": "Send welcome series immediately upon signup",
                "best_time": "Within 1 hour of signup"
            },
            {
                "segment": "At Risk",
                "recommendation": "Send during peak engagement times",
                "best_time": "Wednesday 2:00 PM"
            }
        ]

        return AgentResponse(
            success=True,
            message="Optimal send time analysis complete",
            data={
                "optimal_times": optimal_times,
                "segment_recommendations": segment_recommendations,
            },
            suggestions=["A/B test different send times", "Consider timezone personalization"]
        )

    def _recommend_actions(self) -> AgentResponse:
        """Generate recommended actions based on current data"""
        self.status = AgentStatus.EXECUTING

        all_customers = self.storage.get_all_customers(limit=10000)
        segments = self.storage.get_all_segments()
        campaigns = self.storage.get_all_campaigns()

        recommendations = []

        # Check for high-risk customers without action
        high_risk = [c for c in all_customers if c.churn_risk_score >= 70]
        if high_risk:
            recommendations.append({
                "priority": "high",
                "action": "Launch retention campaign",
                "reason": f"{len(high_risk)} customers at high churn risk",
                "expected_impact": "Prevent 10-20% of at-risk churns",
                "steps": [
                    "Create 'At Risk' segment",
                    "Design win-back email series",
                    "Include special offer or incentive"
                ]
            })

        # Check for new customers needing onboarding
        new_customers = [c for c in all_customers if c.total_purchases <= 1]
        has_onboarding_segment = any("new" in s.name.lower() or "onboard" in s.name.lower() for s in segments)
        if new_customers and not has_onboarding_segment:
            recommendations.append({
                "priority": "high",
                "action": "Create onboarding workflow",
                "reason": f"{len(new_customers)} new customers without nurture sequence",
                "expected_impact": "Increase first purchase conversion by 15-25%",
                "steps": [
                    "Create 'New Customers' segment",
                    "Design 3-step welcome series",
                    "Include first purchase incentive"
                ]
            })

        # Check engagement levels
        low_engagement = [c for c in all_customers if c.engagement_score < 30]
        if len(low_engagement) > len(all_customers) * 0.3:
            recommendations.append({
                "priority": "medium",
                "action": "Launch re-engagement campaign",
                "reason": f"{len(low_engagement)} customers with low engagement",
                "expected_impact": "Re-activate 10-15% of disengaged users",
                "steps": [
                    "Analyze what content resonates",
                    "Create compelling subject lines",
                    "Test different content types"
                ]
            })

        # Suggest segment creation if few exist
        if len(segments) < 3:
            recommendations.append({
                "priority": "medium",
                "action": "Create core customer segments",
                "reason": "Few segments exist for targeted marketing",
                "expected_impact": "Better targeting improves conversion 20-40%",
                "steps": [
                    "Create 'High Value' segment",
                    "Create 'At Risk' segment",
                    "Create 'New Customers' segment"
                ]
            })

        # Use AI for additional recommendations
        if self.ai_available and all_customers:
            summary = f"""
            Total customers: {len(all_customers)}
            Segments: {len(segments)}
            Campaigns: {len(campaigns)}
            High risk customers: {len(high_risk)}
            Low engagement: {len(low_engagement)}
            """
            ai_response = self._call_ai(
                f"Given this marketing data summary, what are 2-3 strategic recommendations?\n{summary}"
            )
            if ai_response:
                ai_data = self._parse_json_response(ai_response)
                if ai_data and "next_steps" in ai_data:
                    for step in ai_data["next_steps"][:3]:
                        recommendations.append({
                            "priority": "medium",
                            "action": step,
                            "reason": "AI-generated strategic recommendation",
                            "expected_impact": "Variable based on implementation",
                            "steps": []
                        })

        return AgentResponse(
            success=True,
            message=f"Generated {len(recommendations)} recommendations",
            data={"recommendations": recommendations},
            suggestions=["Prioritize high-priority actions", "Track impact of implemented changes"]
        )
