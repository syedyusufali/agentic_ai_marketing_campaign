"""
Campaign Executor

Orchestrates campaign execution across channels.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
import uuid

from .campaign import Campaign, CampaignStatus
from .workflow import Workflow, WorkflowExecutor, WorkflowExecution
from .channels import ChannelManager, MessageResult


class CampaignExecutor:
    """
    Executes marketing campaigns.

    Handles:
    - One-time campaign sends
    - Automated workflow campaigns
    - Metrics tracking
    """

    def __init__(self, storage, channel_manager: Optional[ChannelManager] = None):
        self.storage = storage
        self.channel_manager = channel_manager or ChannelManager.create_default()
        self.workflow_executor = WorkflowExecutor(
            storage,
            channel_adapters={
                "email": self.channel_manager.get("email"),
                "sms": self.channel_manager.get("sms"),
                "push": self.channel_manager.get("push"),
            }
        )

        # Execution tracking
        self._executions: Dict[str, Dict] = {}

    def execute_campaign(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Execute a campaign.

        Args:
            campaign: The campaign to execute

        Returns:
            Execution results
        """
        if not campaign.can_start:
            return {
                "success": False,
                "error": f"Campaign cannot be started (status: {campaign.status.value})"
            }

        # Start campaign
        campaign.start()
        self.storage.save_campaign(campaign)

        # Get target customers
        customers = self._get_target_customers(campaign)

        if not customers:
            return {
                "success": False,
                "error": "No customers in target segments"
            }

        execution_id = str(uuid.uuid4())
        results = {
            "execution_id": execution_id,
            "campaign_id": campaign.id,
            "started_at": datetime.utcnow().isoformat(),
            "targeted": len(customers),
            "sent": 0,
            "failed": 0,
            "details": []
        }

        # Execute based on campaign type
        if campaign.workflow:
            # Automated workflow campaign
            workflow = Workflow(
                id=f"{campaign.id}_workflow",
                name=campaign.name,
                **campaign.workflow
            )

            for customer in customers:
                try:
                    execution = self.workflow_executor.start_workflow(
                        workflow, customer.id, campaign.id
                    )
                    results["sent"] += 1
                    results["details"].append({
                        "customer_id": customer.id,
                        "status": "workflow_started",
                        "execution_id": execution.id
                    })
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "customer_id": customer.id,
                        "status": "failed",
                        "error": str(e)
                    })
        else:
            # One-time send
            for customer in customers:
                send_results = self._send_to_customer(campaign, customer)
                if all(r.success for r in send_results):
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                results["details"].append({
                    "customer_id": customer.id,
                    "status": "sent" if send_results else "failed",
                    "channels": [r.channel for r in send_results]
                })

        # Update campaign metrics
        campaign.update_metrics(
            targeted=results["targeted"],
            sent=results["sent"],
            failed=results["failed"]
        )

        # Complete one-time campaigns
        if not campaign.workflow:
            campaign.complete()

        self.storage.save_campaign(campaign)

        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = True

        self._executions[execution_id] = results
        return results

    def _get_target_customers(self, campaign: Campaign) -> List:
        """Get customers in target segments"""
        customers = []
        seen_ids = set()

        for segment_id in campaign.segment_ids:
            segment = self.storage.get_segment(segment_id)
            if segment:
                segment_customers = self.storage.get_customers_in_segment(segment.name)
                for c in segment_customers:
                    if c.id not in seen_ids:
                        customers.append(c)
                        seen_ids.add(c.id)

        # If no segments specified, could target all customers (with limit)
        if not customers and not campaign.segment_ids:
            customers = self.storage.get_all_customers(limit=1000)

        return customers

    def _send_to_customer(self, campaign: Campaign, customer) -> List[MessageResult]:
        """Send campaign content to a customer"""
        results = []

        # Send email content
        if "email" in campaign.content and customer.email:
            email_content = campaign.content["email"]
            result = self.channel_manager.send(
                "email",
                to=customer.email,
                subject=self._personalize(email_content.get("subject", ""), customer),
                body=self._personalize(email_content.get("body", ""), customer),
                preheader=self._personalize(email_content.get("preheader", ""), customer),
            )
            results.append(result)

        # Send SMS content
        if "sms" in campaign.content and customer.phone:
            sms_content = campaign.content["sms"]
            result = self.channel_manager.send(
                "sms",
                to=customer.phone,
                message=self._personalize(sms_content.get("message", ""), customer),
            )
            results.append(result)

        # Send push content
        if "push" in campaign.content:
            push_content = campaign.content["push"]
            # Would need device token from customer
            # Simplified for demo
            pass

        return results

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

    def pause_campaign(self, campaign: Campaign) -> bool:
        """Pause a running campaign"""
        if campaign.status != CampaignStatus.RUNNING:
            return False

        campaign.pause()
        self.storage.save_campaign(campaign)
        return True

    def resume_campaign(self, campaign: Campaign) -> bool:
        """Resume a paused campaign"""
        if campaign.status != CampaignStatus.PAUSED:
            return False

        campaign.resume()
        self.storage.save_campaign(campaign)
        return True

    def cancel_campaign(self, campaign: Campaign) -> bool:
        """Cancel a campaign"""
        campaign.cancel()
        self.storage.save_campaign(campaign)
        return True

    def get_execution(self, execution_id: str) -> Optional[Dict]:
        """Get execution details"""
        return self._executions.get(execution_id)

    def process_pending_workflows(self):
        """
        Process waiting workflow steps.
        Call this periodically to advance workflows.
        """
        from .workflow import WorkflowStatus

        for execution in self.workflow_executor.list_executions():
            if execution.status == WorkflowStatus.WAITING:
                if execution.next_step_at and datetime.utcnow() >= execution.next_step_at:
                    # Time to advance
                    campaign = self.storage.get_campaign(execution.campaign_id)
                    if campaign and campaign.workflow:
                        workflow = Workflow(**campaign.workflow)
                        self.workflow_executor.execute_step(execution, workflow)

    def get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign statistics"""
        campaign = self.storage.get_campaign(campaign_id)
        if not campaign:
            return {}

        # Get workflow executions if applicable
        workflow_stats = {}
        if campaign.workflow:
            executions = self.workflow_executor.list_executions()
            campaign_executions = [e for e in executions if e.campaign_id == campaign_id]

            workflow_stats = {
                "total_in_workflow": len(campaign_executions),
                "completed": sum(1 for e in campaign_executions if e.status.value == "completed"),
                "running": sum(1 for e in campaign_executions if e.status.value == "running"),
                "waiting": sum(1 for e in campaign_executions if e.status.value == "waiting"),
                "failed": sum(1 for e in campaign_executions if e.status.value == "failed"),
            }

        return {
            "campaign": campaign.to_dict(),
            "metrics": campaign.metrics,
            "workflow_stats": workflow_stats,
        }
