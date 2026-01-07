"""
Workflow Execution Engine

Executes multi-step marketing workflows.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
import uuid
import re


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowExecution:
    """
    Tracks a single customer's progress through a workflow.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    customer_id: str = ""
    campaign_id: str = ""

    # Progress
    current_step_id: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    completed_steps: List[str] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    next_step_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "customer_id": self.customer_id,
            "campaign_id": self.campaign_id,
            "current_step_id": self.current_step_id,
            "status": self.status.value,
            "completed_steps": self.completed_steps,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "next_step_at": self.next_step_at.isoformat() if self.next_step_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": self.results,
            "error": self.error,
        }


@dataclass
class Workflow:
    """
    A marketing workflow with steps.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Trigger
    trigger: Dict[str, Any] = field(default_factory=dict)
    # Example: {"type": "segment_entry", "segment": "new_customers"}

    # Steps
    steps: List[Dict[str, Any]] = field(default_factory=list)

    # Exit conditions
    exit_conditions: List[Dict[str, Any]] = field(default_factory=list)
    # Example: [{"event": "purchase"}, {"event": "unsubscribe"}]

    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_step(self, step_id: str) -> Optional[Dict]:
        """Get step by ID"""
        for step in self.steps:
            if step.get("id") == step_id:
                return step
        return None

    def get_first_step(self) -> Optional[Dict]:
        """Get first step"""
        return self.steps[0] if self.steps else None

    def get_next_step(self, current_step_id: str, branch: Optional[str] = None) -> Optional[Dict]:
        """Get next step after current"""
        current = self.get_step(current_step_id)
        if not current:
            return None

        # Handle branching
        if current.get("type") == "condition" and current.get("branches"):
            for b in current["branches"]:
                if b.get("condition") == branch or branch is None:
                    return self.get_step(b.get("next"))

        next_id = current.get("next")
        return self.get_step(next_id) if next_id else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger,
            "steps": self.steps,
            "exit_conditions": self.exit_conditions,
            "settings": self.settings,
            "created_at": self.created_at.isoformat(),
        }


class WorkflowExecutor:
    """
    Executes workflow steps for customers.
    """

    def __init__(self, storage, channel_adapters: Dict = None):
        self.storage = storage
        self.channel_adapters = channel_adapters or {}
        self._executions: Dict[str, WorkflowExecution] = {}

    def start_workflow(
        self,
        workflow: Workflow,
        customer_id: str,
        campaign_id: str = ""
    ) -> WorkflowExecution:
        """
        Start a workflow for a customer.

        Args:
            workflow: The workflow to execute
            customer_id: Customer ID
            campaign_id: Associated campaign ID

        Returns:
            WorkflowExecution tracking object
        """
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            customer_id=customer_id,
            campaign_id=campaign_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        # Get first step
        first_step = workflow.get_first_step()
        if first_step:
            execution.current_step_id = first_step.get("id")

        self._executions[execution.id] = execution
        return execution

    def execute_step(
        self,
        execution: WorkflowExecution,
        workflow: Workflow
    ) -> WorkflowExecution:
        """
        Execute the current step and advance.

        Args:
            execution: Current execution state
            workflow: The workflow definition

        Returns:
            Updated execution
        """
        if execution.status not in [WorkflowStatus.RUNNING, WorkflowStatus.WAITING]:
            return execution

        current_step = workflow.get_step(execution.current_step_id)
        if not current_step:
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            return execution

        step_type = current_step.get("type", "")
        config = current_step.get("config", {})

        try:
            # Execute based on step type
            if step_type == "send_email":
                self._execute_send_email(execution, config)
                execution.completed_steps.append(execution.current_step_id)

            elif step_type == "send_sms":
                self._execute_send_sms(execution, config)
                execution.completed_steps.append(execution.current_step_id)

            elif step_type == "send_push":
                self._execute_send_push(execution, config)
                execution.completed_steps.append(execution.current_step_id)

            elif step_type == "wait":
                wait_until = self._calculate_wait_time(config)
                if datetime.utcnow() >= wait_until:
                    execution.completed_steps.append(execution.current_step_id)
                else:
                    execution.status = WorkflowStatus.WAITING
                    execution.next_step_at = wait_until
                    return execution

            elif step_type == "condition":
                # Evaluate condition
                branch = self._evaluate_condition(execution, config)
                next_step = workflow.get_next_step(execution.current_step_id, branch)
                if next_step:
                    execution.current_step_id = next_step.get("id")
                else:
                    execution.status = WorkflowStatus.COMPLETED
                    execution.completed_at = datetime.utcnow()
                return execution

            elif step_type == "update_profile":
                self._execute_update_profile(execution, config)
                execution.completed_steps.append(execution.current_step_id)

            elif step_type == "webhook":
                self._execute_webhook(execution, config)
                execution.completed_steps.append(execution.current_step_id)

            elif step_type == "end":
                execution.status = WorkflowStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                return execution

            # Advance to next step
            next_step = workflow.get_next_step(execution.current_step_id)
            if next_step:
                execution.current_step_id = next_step.get("id")
                execution.status = WorkflowStatus.RUNNING
            else:
                execution.status = WorkflowStatus.COMPLETED
                execution.completed_at = datetime.utcnow()

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)

        return execution

    def _execute_send_email(self, execution: WorkflowExecution, config: Dict):
        """Execute email send step"""
        customer = self.storage.get_customer(execution.customer_id)
        if not customer or not customer.email:
            return

        template = config.get("template", "")
        subject = config.get("subject", "")
        body = config.get("body", "")

        # Personalize
        subject = self._personalize(subject, customer)
        body = self._personalize(body, customer)

        # Send via channel adapter
        if "email" in self.channel_adapters:
            self.channel_adapters["email"].send(
                to=customer.email,
                subject=subject,
                body=body,
            )

        # Record result
        execution.results[execution.current_step_id] = {
            "type": "email",
            "sent_to": customer.email,
            "sent_at": datetime.utcnow().isoformat(),
        }

    def _execute_send_sms(self, execution: WorkflowExecution, config: Dict):
        """Execute SMS send step"""
        customer = self.storage.get_customer(execution.customer_id)
        if not customer or not customer.phone:
            return

        message = config.get("message", "")
        message = self._personalize(message, customer)

        if "sms" in self.channel_adapters:
            self.channel_adapters["sms"].send(
                to=customer.phone,
                message=message,
            )

        execution.results[execution.current_step_id] = {
            "type": "sms",
            "sent_to": customer.phone,
            "sent_at": datetime.utcnow().isoformat(),
        }

    def _execute_send_push(self, execution: WorkflowExecution, config: Dict):
        """Execute push notification step"""
        # In real implementation, would send push via adapter
        execution.results[execution.current_step_id] = {
            "type": "push",
            "sent_at": datetime.utcnow().isoformat(),
        }

    def _execute_update_profile(self, execution: WorkflowExecution, config: Dict):
        """Execute profile update step"""
        customer = self.storage.get_customer(execution.customer_id)
        if not customer:
            return

        updates = config.get("updates", {})
        for key, value in updates.items():
            if hasattr(customer, key):
                setattr(customer, key, value)

        self.storage.save_customer(customer)

    def _execute_webhook(self, execution: WorkflowExecution, config: Dict):
        """Execute webhook step"""
        # In real implementation, would call external webhook
        url = config.get("url", "")
        execution.results[execution.current_step_id] = {
            "type": "webhook",
            "url": url,
            "sent_at": datetime.utcnow().isoformat(),
        }

    def _calculate_wait_time(self, config: Dict) -> datetime:
        """Calculate when wait step should complete"""
        duration = config.get("duration", "1 day")
        now = datetime.utcnow()

        # Parse duration
        duration_lower = duration.lower()

        hours_match = re.search(r'(\d+)\s*hour', duration_lower)
        if hours_match:
            return now + timedelta(hours=int(hours_match.group(1)))

        days_match = re.search(r'(\d+)\s*day', duration_lower)
        if days_match:
            return now + timedelta(days=int(days_match.group(1)))

        weeks_match = re.search(r'(\d+)\s*week', duration_lower)
        if weeks_match:
            return now + timedelta(weeks=int(weeks_match.group(1)))

        # Default: 1 day
        return now + timedelta(days=1)

    def _evaluate_condition(self, execution: WorkflowExecution, config: Dict) -> str:
        """Evaluate a condition and return branch"""
        condition = config.get("condition", "")
        customer = self.storage.get_customer(execution.customer_id)

        if not customer:
            return "false"

        # Simple condition evaluation
        if "total_purchases == 0" in condition:
            return "true" if customer.total_purchases == 0 else "false"

        if "email_opened == true" in condition:
            # Check if email was opened (would need to check events)
            return "true"  # Simplified

        if "cart_converted == false" in condition:
            return "true"  # Simplified

        return "true"

    def _personalize(self, text: str, customer) -> str:
        """Personalize text with customer data"""
        if not text:
            return text

        replacements = {
            "{{first_name}}": customer.first_name or "there",
            "{{last_name}}": customer.last_name or "",
            "{{full_name}}": customer.full_name,
            "{{email}}": customer.email or "",
            "{{location}}": customer.location or "",
        }

        result = text
        for token, value in replacements.items():
            result = result.replace(token, str(value))

        return result

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID"""
        return self._executions.get(execution_id)

    def list_executions(self, workflow_id: Optional[str] = None) -> List[WorkflowExecution]:
        """List all executions, optionally filtered by workflow"""
        executions = list(self._executions.values())
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        return executions
