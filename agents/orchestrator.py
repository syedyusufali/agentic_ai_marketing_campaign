"""
Orchestrator Agent

Central coordinator that routes requests to specialized agents
and manages complex multi-step marketing operations.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
import re

from .base_agent import BaseAgent, AgentResponse, AgentStatus, AgentRegistry
from .segmentation_agent import SegmentationAgent
from .content_agent import ContentAgent
from .workflow_agent import WorkflowAgent
from .analytics_agent import AnalyticsAgent


class OrchestratorAgent(BaseAgent):
    """
    Master orchestrator that coordinates all AI agents.

    Capabilities:
    - Parse natural language requests
    - Route to appropriate specialized agents
    - Coordinate multi-step campaigns
    - Manage agent collaboration
    """

    def __init__(self, storage, use_ai: bool = True):
        super().__init__(
            storage=storage,
            name="OrchestratorAgent",
            description="Coordinates all AI agents and handles natural language requests",
            use_ai=use_ai
        )

        # Initialize specialized agents
        self.segmentation_agent = SegmentationAgent(storage, use_ai)
        self.content_agent = ContentAgent(storage, use_ai)
        self.workflow_agent = WorkflowAgent(storage, use_ai)
        self.analytics_agent = AnalyticsAgent(storage, use_ai)

        # Register agents
        self.registry = AgentRegistry()
        self.registry.register(self.segmentation_agent)
        self.registry.register(self.content_agent)
        self.registry.register(self.workflow_agent)
        self.registry.register(self.analytics_agent)

        # Intent patterns
        self._intent_patterns = self._build_intent_patterns()

    def get_system_prompt(self) -> str:
        return """You are a marketing campaign orchestrator AI. You understand marketing requests and coordinate specialized agents to fulfill them.

Your role:
1. Understand the user's marketing goal
2. Break down complex requests into tasks
3. Route tasks to the right specialized agents
4. Combine results into a coherent response

Available agents:
- SegmentationAgent: Creates customer segments, discovers audiences
- ContentAgent: Generates marketing content (email, SMS, push)
- WorkflowAgent: Designs automated marketing workflows
- AnalyticsAgent: Analyzes performance, predicts outcomes

When parsing requests, output JSON:
{
    "intent": "create_campaign|analyze|segment|content|workflow|info",
    "tasks": [
        {
            "agent": "segmentation|content|workflow|analytics",
            "action": "description of what to do",
            "params": {}
        }
    ],
    "reasoning": "why this breakdown"
}

For complex campaigns, you may need multiple agents working together.
"""

    def get_capabilities(self) -> List[str]:
        return [
            "parse_request",
            "route_to_agent",
            "create_campaign",
            "orchestrate_multi_step",
            "get_status",
        ]

    def can_handle(self, task: str) -> bool:
        # Orchestrator can handle anything
        return True

    def execute(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Execute an orchestrated task.

        Args:
            task: Natural language task/request
            context: Optional context

        Returns:
            Combined AgentResponse from all involved agents
        """
        import time
        start_time = time.time()
        self.status = AgentStatus.THINKING
        context = context or {}

        try:
            # Parse the intent
            intent, tasks = self._parse_intent(task)

            # Handle special intents
            if intent == "help":
                return self._get_help()

            if intent == "status":
                return self._get_status()

            if intent == "list":
                return self._handle_list(task)

            # Route to agents
            results = []
            for agent_task in tasks:
                agent_name = agent_task.get("agent", "")
                action = agent_task.get("action", task)
                params = agent_task.get("params", {})

                agent = self._get_agent(agent_name)
                if agent:
                    result = agent.execute(action, {**context, **params})
                    results.append({
                        "agent": agent_name,
                        "response": result
                    })

            # Combine results
            combined = self._combine_results(results)
            combined.execution_time_ms = (time.time() - start_time) * 1000

            self.status = AgentStatus.COMPLETED
            self._log_execution(task, combined, context)

            return combined

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResponse(
                success=False,
                message=f"Orchestration error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _parse_intent(self, task: str) -> tuple:
        """Parse user intent from natural language"""
        task_lower = task.lower().strip()

        # Check for direct commands
        if task_lower in ["help", "?"]:
            return "help", []

        if task_lower in ["status", "dashboard", "overview"]:
            return "status", []

        if task_lower.startswith("list"):
            return "list", []

        # Try AI parsing for complex requests
        if self.ai_available:
            ai_response = self._call_ai(
                f"Parse this marketing request and determine the intent and tasks:\n\n{task}"
            )
            if ai_response:
                parsed = self._parse_json_response(ai_response)
                if parsed and "intent" in parsed:
                    return parsed.get("intent"), parsed.get("tasks", [])

        # Rule-based intent detection
        intent, agent = self._detect_intent(task_lower)

        tasks = [{
            "agent": agent,
            "action": task,
            "params": {}
        }] if agent else []

        return intent, tasks

    def _detect_intent(self, task: str) -> tuple:
        """Detect intent using pattern matching"""
        for pattern, (intent, agent) in self._intent_patterns.items():
            if re.search(pattern, task):
                return intent, agent

        # Default: try analytics for general queries
        return "query", "analytics"

    def _build_intent_patterns(self) -> Dict:
        """Build intent detection patterns"""
        return {
            # Segmentation patterns
            r"(create|build|make).*(segment|audience)": ("segment", "segmentation"),
            r"(find|discover|identify).*(customer|user|segment)": ("segment", "segmentation"),
            r"(target|targeting)": ("segment", "segmentation"),
            r"who (are|is|should)": ("segment", "segmentation"),
            r"segment.*(high value|churning|new|active)": ("segment", "segmentation"),

            # Content patterns
            r"(write|create|generate).*(email|sms|push|content|copy)": ("content", "content"),
            r"(subject line|email subject)": ("content", "content"),
            r"(a/b|variant|test).*(content|email)": ("content", "content"),

            # Workflow patterns
            r"(create|build|design).*(workflow|automation|flow|sequence)": ("workflow", "workflow"),
            r"(onboarding|winback|nurture|drip)": ("workflow", "workflow"),
            r"(automate|automated)": ("workflow", "workflow"),

            # Analytics patterns
            r"(analyze|analysis|report|insight)": ("analytics", "analytics"),
            r"(performance|metric|stat|dashboard)": ("analytics", "analytics"),
            r"(predict|churn|risk|health)": ("analytics", "analytics"),
            r"(recommend|suggest|should i)": ("analytics", "analytics"),
            r"how (is|are|well)": ("analytics", "analytics"),

            # Campaign patterns
            r"(create|launch|run|start).*(campaign)": ("campaign", "orchestrate"),
            r"(campaign).*(for|targeting)": ("campaign", "orchestrate"),
        }

    def _get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get agent by name"""
        agent_map = {
            "segmentation": self.segmentation_agent,
            "segment": self.segmentation_agent,
            "content": self.content_agent,
            "workflow": self.workflow_agent,
            "analytics": self.analytics_agent,
            "orchestrate": self,  # Self-reference for complex operations
        }
        return agent_map.get(agent_name.lower())

    def _combine_results(self, results: List[Dict]) -> AgentResponse:
        """Combine results from multiple agents"""
        if not results:
            return AgentResponse(
                success=True,
                message="No actions taken",
                data={}
            )

        if len(results) == 1:
            return results[0]["response"]

        # Multiple results - combine them
        all_success = all(r["response"].success for r in results)
        messages = [f"[{r['agent']}] {r['response'].message}" for r in results]
        combined_data = {
            r["agent"]: r["response"].data
            for r in results
        }

        all_actions = []
        all_suggestions = []
        for r in results:
            all_actions.extend(r["response"].actions_taken)
            all_suggestions.extend(r["response"].suggestions)

        return AgentResponse(
            success=all_success,
            message="\n".join(messages),
            data=combined_data,
            actions_taken=all_actions,
            suggestions=list(set(all_suggestions)),
        )

    def _get_help(self) -> AgentResponse:
        """Return help information"""
        help_text = """
**Agentic AI Marketing Platform**

I can help you with:

**Segments & Audiences**
- "Create a segment for high-value customers"
- "Find customers who haven't purchased in 30 days"
- "Discover potential segments"

**Content Creation**
- "Write a welcome email for new customers"
- "Generate SMS for a flash sale"
- "Create A/B variants for subject lines"

**Workflows & Automation**
- "Build an onboarding workflow"
- "Create a cart abandonment sequence"
- "Design a win-back campaign"

**Analytics & Insights**
- "Show me platform health"
- "Analyze churn risk"
- "Get campaign recommendations"

**Campaigns**
- "Create a winback campaign for inactive users"
- "Launch a holiday promotion"

Just describe what you want in natural language!
"""
        return AgentResponse(
            success=True,
            message=help_text,
            data={"agents": self.registry.list_agents()}
        )

    def _get_status(self) -> AgentResponse:
        """Get platform status overview"""
        return self.analytics_agent.execute("Get platform health overview")

    def _handle_list(self, task: str) -> AgentResponse:
        """Handle list commands"""
        task_lower = task.lower()

        if "segment" in task_lower:
            segments = self.storage.get_all_segments()
            return AgentResponse(
                success=True,
                message=f"Found {len(segments)} segments",
                data={"segments": [s.to_dict() for s in segments]}
            )

        if "campaign" in task_lower:
            campaigns = self.storage.get_all_campaigns()
            return AgentResponse(
                success=True,
                message=f"Found {len(campaigns)} campaigns",
                data={"campaigns": [c.to_dict() for c in campaigns]}
            )

        if "customer" in task_lower:
            count = self.storage.count_customers()
            return AgentResponse(
                success=True,
                message=f"Total customers: {count}",
                data={"total_customers": count}
            )

        return AgentResponse(
            success=True,
            message="Available lists: segments, campaigns, customers"
        )

    def create_campaign(
        self,
        goal: str,
        segment_name: Optional[str] = None,
        channel: str = "email"
    ) -> AgentResponse:
        """
        Create a complete campaign orchestrating multiple agents.

        Args:
            goal: Campaign goal in natural language
            segment_name: Target segment (will create if not exists)
            channel: Primary channel

        Returns:
            Combined response with campaign details
        """
        results = []
        actions = []

        # Step 1: Create or get segment
        if segment_name:
            segment = self.storage.get_segment_by_name(segment_name)
            if not segment:
                seg_result = self.segmentation_agent.execute(
                    f"Create segment: {segment_name}"
                )
                results.append(("Segmentation", seg_result))
                actions.append(f"Created segment: {segment_name}")
        else:
            # Auto-discover appropriate segment
            seg_result = self.segmentation_agent.execute(
                f"Create segment for: {goal}"
            )
            results.append(("Segmentation", seg_result))
            if seg_result.data and "segment" in seg_result.data:
                segment_name = seg_result.data["segment"].get("name")
                actions.append(f"Created segment: {segment_name}")

        # Step 2: Generate content
        content_result = self.content_agent.execute(
            f"Generate {channel} content for: {goal}"
        )
        results.append(("Content", content_result))
        actions.append(f"Generated {channel} content")

        # Step 3: Design workflow (if applicable)
        if any(kw in goal.lower() for kw in ["series", "sequence", "workflow", "automated"]):
            workflow_result = self.workflow_agent.execute(
                f"Design workflow for: {goal}"
            )
            results.append(("Workflow", workflow_result))
            actions.append("Designed automation workflow")

        # Combine all results
        success = all(r[1].success for r in results)
        combined_data = {
            name.lower(): result.data
            for name, result in results
        }

        return AgentResponse(
            success=success,
            message=f"Campaign created: {goal}",
            data={
                "campaign_goal": goal,
                "segment": segment_name,
                "channel": channel,
                "details": combined_data
            },
            actions_taken=actions,
            suggestions=[
                "Review generated content",
                "Adjust segment criteria if needed",
                "Schedule or launch the campaign"
            ]
        )

    def process(self, user_input: str) -> str:
        """
        Process user input and return formatted response.
        This is the main entry point for the CLI.

        Args:
            user_input: Natural language input from user

        Returns:
            Formatted response string
        """
        response = self.execute(user_input)

        # Format response for CLI output
        output = []

        if response.success:
            output.append(response.message)
        else:
            output.append(f"Error: {response.message}")

        if response.data:
            output.append("\n" + self._format_data(response.data))

        if response.actions_taken:
            output.append("\nActions taken:")
            for action in response.actions_taken:
                output.append(f"  - {action}")

        if response.suggestions:
            output.append("\nSuggestions:")
            for suggestion in response.suggestions:
                output.append(f"  - {suggestion}")

        return "\n".join(output)

    def _format_data(self, data: Any, indent: int = 0) -> str:
        """Format data for display"""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{'  ' * indent}{key}:")
                    lines.append(self._format_data(value, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}{key}: {value}")
            return "\n".join(lines)
        elif isinstance(data, list):
            if not data:
                return f"{'  ' * indent}(empty)"
            lines = []
            for item in data[:5]:  # Limit to first 5
                if isinstance(item, dict):
                    # Show key fields
                    summary = item.get("name") or item.get("id") or str(item)[:50]
                    lines.append(f"{'  ' * indent}- {summary}")
                else:
                    lines.append(f"{'  ' * indent}- {item}")
            if len(data) > 5:
                lines.append(f"{'  ' * indent}... and {len(data) - 5} more")
            return "\n".join(lines)
        else:
            return f"{'  ' * indent}{data}"
