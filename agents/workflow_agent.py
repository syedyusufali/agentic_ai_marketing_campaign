"""
Workflow Agent

Designs and optimizes customer marketing workflows.
Uses AI to create multi-step automated campaigns.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
import uuid

from .base_agent import BaseAgent, AgentResponse, AgentStatus


class WorkflowStepType:
    """Types of workflow steps"""
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    SEND_PUSH = "send_push"
    WAIT = "wait"
    CONDITION = "condition"
    SPLIT = "split"  # A/B split
    UPDATE_PROFILE = "update_profile"
    WEBHOOK = "webhook"
    END = "end"


class WorkflowAgent(BaseAgent):
    """
    AI agent for designing marketing workflows.

    Capabilities:
    - Design multi-step workflows from goals
    - Create branching logic
    - Optimize workflow timing
    - Recommend workflow improvements
    """

    def __init__(self, storage, use_ai: bool = True):
        super().__init__(
            storage=storage,
            name="WorkflowAgent",
            description="Designs automated marketing workflows using AI",
            use_ai=use_ai
        )

        # Workflow templates
        self._templates = self._load_templates()

    def get_system_prompt(self) -> str:
        return """You are a marketing automation expert AI. You design effective customer workflows.

When designing workflows, output JSON:
{
    "name": "Workflow Name",
    "description": "What this workflow achieves",
    "trigger": {
        "type": "segment_entry|event|schedule",
        "config": {}
    },
    "steps": [
        {
            "id": "step_1",
            "type": "send_email|send_sms|wait|condition|split|end",
            "config": {
                "template": "template_name or content description",
                "duration": "for wait steps (e.g., '2 days')",
                "condition": "for condition steps"
            },
            "next": "step_2 or null for end",
            "branches": [for condition steps, list of {condition, next}]
        }
    ],
    "reasoning": "Why this workflow structure works"
}

Workflow best practices:
- Start with value, don't immediately sell
- Space out communications (2-3 days minimum between touches)
- Use conditions to personalize paths
- Include exit conditions (purchase, unsubscribe)
- 3-5 steps is optimal for most workflows
- End with clear CTA
"""

    def get_capabilities(self) -> List[str]:
        return [
            "design_workflow",
            "optimize_workflow",
            "create_onboarding_flow",
            "create_winback_flow",
            "create_nurture_flow",
        ]

    def can_handle(self, task: str) -> bool:
        task_lower = task.lower()
        keywords = ["workflow", "automation", "flow", "sequence", "drip", "nurture", "onboarding"]
        return any(kw in task_lower for kw in keywords)

    def execute(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """Execute workflow design task"""
        import time
        start_time = time.time()
        self.status = AgentStatus.THINKING
        context = context or {}

        try:
            task_lower = task.lower()

            if "optimize" in task_lower:
                workflow_id = context.get("workflow_id")
                response = self._optimize_workflow(workflow_id)
            elif "template" in task_lower or "list" in task_lower:
                response = self._list_templates()
            else:
                # Design new workflow
                response = self._design_workflow(task, context)

            self.status = AgentStatus.COMPLETED
            response.execution_time_ms = (time.time() - start_time) * 1000
            self._log_execution(task, response, context)
            return response

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResponse(
                success=False,
                message=f"Workflow design error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _design_workflow(self, goal: str, context: Dict) -> AgentResponse:
        """Design a workflow based on the goal"""
        self.status = AgentStatus.EXECUTING

        # Try AI first
        ai_prompt = f"""Design a marketing workflow for: {goal}

Target segment: {context.get('segment', 'general customers')}
Channel preference: {context.get('channel', 'email')}

Return the workflow as JSON."""

        ai_response = self._call_ai(ai_prompt)
        workflow_data = None

        if ai_response:
            workflow_data = self._parse_json_response(ai_response)

        # Fallback to templates
        if not workflow_data:
            workflow_data = self._create_from_template(goal)

        if not workflow_data:
            return AgentResponse(
                success=False,
                message="Could not design workflow from goal",
                suggestions=["Try specifying the workflow type (onboarding, winback, etc.)"]
            )

        # Validate and enhance workflow
        workflow = self._validate_workflow(workflow_data)

        return AgentResponse(
            success=True,
            message=f"Designed workflow: {workflow['name']}",
            data={
                "workflow": workflow,
                "estimated_duration": self._estimate_duration(workflow),
                "step_count": len(workflow.get("steps", [])),
            },
            actions_taken=["Designed workflow", "Validated step sequence"],
            reasoning=workflow_data.get("reasoning", "Based on best practices"),
            confidence=0.85 if ai_response else 0.7
        )

    def _create_from_template(self, goal: str) -> Optional[Dict]:
        """Create workflow from matching template"""
        goal_lower = goal.lower()

        # Match goal to template
        if any(kw in goal_lower for kw in ["onboard", "welcome", "new customer", "new user"]):
            return self._templates["onboarding"]
        elif any(kw in goal_lower for kw in ["winback", "win back", "inactive", "churning", "lapsed"]):
            return self._templates["winback"]
        elif any(kw in goal_lower for kw in ["cart", "abandon"]):
            return self._templates["cart_abandonment"]
        elif any(kw in goal_lower for kw in ["nurture", "education", "engage"]):
            return self._templates["nurture"]
        elif any(kw in goal_lower for kw in ["upsell", "cross-sell", "recommend"]):
            return self._templates["upsell"]

        # Default: simple promotional workflow
        return self._templates.get("promotional")

    def _validate_workflow(self, workflow: Dict) -> Dict:
        """Validate and enhance workflow structure"""
        # Ensure required fields
        if "id" not in workflow:
            workflow["id"] = str(uuid.uuid4())
        if "name" not in workflow:
            workflow["name"] = "Custom Workflow"
        if "steps" not in workflow:
            workflow["steps"] = []

        # Ensure step IDs and connections
        steps = workflow.get("steps", [])
        for i, step in enumerate(steps):
            if "id" not in step:
                step["id"] = f"step_{i+1}"
            if "next" not in step and i < len(steps) - 1:
                step["next"] = steps[i + 1].get("id", f"step_{i+2}")
            elif i == len(steps) - 1:
                step["next"] = None

        # Add metadata
        workflow["created_at"] = datetime.utcnow().isoformat()
        workflow["status"] = "draft"

        return workflow

    def _estimate_duration(self, workflow: Dict) -> str:
        """Estimate total workflow duration"""
        total_days = 0
        for step in workflow.get("steps", []):
            if step.get("type") == WorkflowStepType.WAIT:
                duration = step.get("config", {}).get("duration", "")
                days = self._parse_duration(duration)
                total_days += days

        if total_days == 0:
            return "Immediate"
        elif total_days == 1:
            return "1 day"
        else:
            return f"{total_days} days"

    def _parse_duration(self, duration: str) -> int:
        """Parse duration string to days"""
        import re
        duration = duration.lower()

        hours_match = re.search(r'(\d+)\s*hour', duration)
        if hours_match:
            return max(1, int(hours_match.group(1)) // 24)

        days_match = re.search(r'(\d+)\s*day', duration)
        if days_match:
            return int(days_match.group(1))

        weeks_match = re.search(r'(\d+)\s*week', duration)
        if weeks_match:
            return int(weeks_match.group(1)) * 7

        return 0

    def _optimize_workflow(self, workflow_id: Optional[str]) -> AgentResponse:
        """Suggest optimizations for a workflow"""
        suggestions = [
            {
                "type": "timing",
                "suggestion": "Consider sending emails between 10 AM - 2 PM for higher open rates",
                "impact": "10-15% improvement in open rates"
            },
            {
                "type": "personalization",
                "suggestion": "Add dynamic content blocks based on purchase history",
                "impact": "20% improvement in click rates"
            },
            {
                "type": "branching",
                "suggestion": "Add a condition to skip promotional emails for recent purchasers",
                "impact": "Reduced unsubscribes"
            },
            {
                "type": "timing",
                "suggestion": "Reduce wait time between first two emails from 3 to 2 days",
                "impact": "Faster conversion for engaged users"
            }
        ]

        return AgentResponse(
            success=True,
            message=f"Generated {len(suggestions)} optimization suggestions",
            data={"suggestions": suggestions}
        )

    def _list_templates(self) -> AgentResponse:
        """List available workflow templates"""
        templates_info = [
            {
                "id": key,
                "name": value.get("name"),
                "description": value.get("description"),
                "steps": len(value.get("steps", [])),
            }
            for key, value in self._templates.items()
        ]

        return AgentResponse(
            success=True,
            message=f"Found {len(templates_info)} workflow templates",
            data={"templates": templates_info}
        )

    def _load_templates(self) -> Dict[str, Dict]:
        """Load workflow templates"""
        return {
            "onboarding": {
                "name": "Welcome Series",
                "description": "3-step onboarding workflow for new customers",
                "trigger": {
                    "type": "segment_entry",
                    "config": {"segment": "new_customers"}
                },
                "steps": [
                    {
                        "id": "step_1",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "welcome",
                            "subject": "Welcome to the family, {{first_name}}!"
                        },
                        "next": "step_2"
                    },
                    {
                        "id": "step_2",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "2 days"},
                        "next": "step_3"
                    },
                    {
                        "id": "step_3",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "onboarding_tips",
                            "subject": "{{first_name}}, here's how to get started"
                        },
                        "next": "step_4"
                    },
                    {
                        "id": "step_4",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "3 days"},
                        "next": "step_5"
                    },
                    {
                        "id": "step_5",
                        "type": WorkflowStepType.CONDITION,
                        "config": {
                            "condition": "total_purchases == 0"
                        },
                        "branches": [
                            {"condition": "true", "next": "step_6"},
                            {"condition": "false", "next": "step_end"}
                        ]
                    },
                    {
                        "id": "step_6",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "first_purchase_incentive",
                            "subject": "{{first_name}}, your exclusive welcome offer awaits"
                        },
                        "next": "step_end"
                    },
                    {
                        "id": "step_end",
                        "type": WorkflowStepType.END,
                        "config": {},
                        "next": None
                    }
                ],
                "reasoning": "Progressive engagement with incentive for non-converters"
            },
            "winback": {
                "name": "Win-back Campaign",
                "description": "Re-engage inactive customers",
                "trigger": {
                    "type": "segment_entry",
                    "config": {"segment": "inactive_30_days"}
                },
                "steps": [
                    {
                        "id": "step_1",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "winback",
                            "subject": "We miss you, {{first_name}}!"
                        },
                        "next": "step_2"
                    },
                    {
                        "id": "step_2",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "3 days"},
                        "next": "step_3"
                    },
                    {
                        "id": "step_3",
                        "type": WorkflowStepType.CONDITION,
                        "config": {"condition": "email_opened == true"},
                        "branches": [
                            {"condition": "true", "next": "step_4"},
                            {"condition": "false", "next": "step_5"}
                        ]
                    },
                    {
                        "id": "step_4",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "winback_offer",
                            "subject": "{{first_name}}, here's 20% off to welcome you back"
                        },
                        "next": "step_end"
                    },
                    {
                        "id": "step_5",
                        "type": WorkflowStepType.SEND_SMS,
                        "config": {
                            "template": "winback_sms",
                            "message": "{{first_name}}, we miss you! Reply BACK for 20% off"
                        },
                        "next": "step_end"
                    },
                    {
                        "id": "step_end",
                        "type": WorkflowStepType.END,
                        "config": {},
                        "next": None
                    }
                ],
                "reasoning": "Multi-channel approach with conditional paths"
            },
            "cart_abandonment": {
                "name": "Cart Recovery",
                "description": "Recover abandoned shopping carts",
                "trigger": {
                    "type": "event",
                    "config": {"event": "add_to_cart", "condition": "no_purchase_24h"}
                },
                "steps": [
                    {
                        "id": "step_1",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "1 hour"},
                        "next": "step_2"
                    },
                    {
                        "id": "step_2",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "cart_abandonment",
                            "subject": "{{first_name}}, you forgot something!"
                        },
                        "next": "step_3"
                    },
                    {
                        "id": "step_3",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "24 hours"},
                        "next": "step_4"
                    },
                    {
                        "id": "step_4",
                        "type": WorkflowStepType.CONDITION,
                        "config": {"condition": "cart_converted == false"},
                        "branches": [
                            {"condition": "true", "next": "step_5"},
                            {"condition": "false", "next": "step_end"}
                        ]
                    },
                    {
                        "id": "step_5",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "cart_incentive",
                            "subject": "{{first_name}}, complete your order with 10% off"
                        },
                        "next": "step_end"
                    },
                    {
                        "id": "step_end",
                        "type": WorkflowStepType.END,
                        "config": {},
                        "next": None
                    }
                ],
                "reasoning": "Quick first touch, incentive for persistent abandoners"
            },
            "nurture": {
                "name": "Lead Nurture",
                "description": "Educate and nurture leads to conversion",
                "trigger": {
                    "type": "segment_entry",
                    "config": {"segment": "leads"}
                },
                "steps": [
                    {
                        "id": "step_1",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "educational_1",
                            "subject": "{{first_name}}, here's a guide to get started"
                        },
                        "next": "step_2"
                    },
                    {
                        "id": "step_2",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "4 days"},
                        "next": "step_3"
                    },
                    {
                        "id": "step_3",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "educational_2",
                            "subject": "5 tips you need to know"
                        },
                        "next": "step_4"
                    },
                    {
                        "id": "step_4",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "4 days"},
                        "next": "step_5"
                    },
                    {
                        "id": "step_5",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "soft_sell",
                            "subject": "Ready to take the next step?"
                        },
                        "next": "step_end"
                    },
                    {
                        "id": "step_end",
                        "type": WorkflowStepType.END,
                        "config": {},
                        "next": None
                    }
                ],
                "reasoning": "Education-first approach leading to soft conversion"
            },
            "upsell": {
                "name": "Post-Purchase Upsell",
                "description": "Upsell and cross-sell after purchase",
                "trigger": {
                    "type": "event",
                    "config": {"event": "purchase"}
                },
                "steps": [
                    {
                        "id": "step_1",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "3 days"},
                        "next": "step_2"
                    },
                    {
                        "id": "step_2",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "cross_sell",
                            "subject": "{{first_name}}, customers who bought this also love..."
                        },
                        "next": "step_3"
                    },
                    {
                        "id": "step_3",
                        "type": WorkflowStepType.WAIT,
                        "config": {"duration": "7 days"},
                        "next": "step_4"
                    },
                    {
                        "id": "step_4",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "review_request",
                            "subject": "{{first_name}}, how was your purchase?"
                        },
                        "next": "step_end"
                    },
                    {
                        "id": "step_end",
                        "type": WorkflowStepType.END,
                        "config": {},
                        "next": None
                    }
                ],
                "reasoning": "Cross-sell followed by review request for engagement"
            },
            "promotional": {
                "name": "Promotional Campaign",
                "description": "Single promotional email campaign",
                "trigger": {
                    "type": "schedule",
                    "config": {"schedule": "immediate"}
                },
                "steps": [
                    {
                        "id": "step_1",
                        "type": WorkflowStepType.SEND_EMAIL,
                        "config": {
                            "template": "promotional",
                            "subject": "{{first_name}}, exclusive offer inside!"
                        },
                        "next": "step_end"
                    },
                    {
                        "id": "step_end",
                        "type": WorkflowStepType.END,
                        "config": {},
                        "next": None
                    }
                ],
                "reasoning": "Simple single-touch promotional campaign"
            }
        }

    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get a specific workflow template"""
        return self._templates.get(template_id)
