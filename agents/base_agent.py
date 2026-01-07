"""
Base Agent Framework

Provides the foundation for all AI agents in the platform.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
import json
import os


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentResponse:
    """
    Standardized response from an agent.
    """
    success: bool = True
    message: str = ""
    data: Any = None
    actions_taken: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 0-1 confidence in the response
    reasoning: str = ""  # Agent's reasoning process
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "actions_taken": self.actions_taken,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "execution_time_ms": self.execution_time_ms,
        }


class BaseAgent(ABC):
    """
    Base class for all AI agents.

    Provides:
    - AI model integration (Anthropic/OpenAI)
    - Fallback to rule-based logic
    - Standardized input/output
    - Execution tracking
    """

    def __init__(
        self,
        storage,
        name: str = "BaseAgent",
        description: str = "",
        use_ai: bool = True
    ):
        self.storage = storage
        self.name = name
        self.description = description
        self.use_ai = use_ai
        self.status = AgentStatus.IDLE

        # AI configuration
        self.ai_provider = os.getenv("AI_PROVIDER", "anthropic")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        # Check if AI is available
        self.ai_available = bool(self.anthropic_key or self.openai_key)

        # Execution history
        self.execution_history: List[Dict] = []

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass

    @abstractmethod
    def execute(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """Execute the agent's primary function"""
        pass

    def _call_ai(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Call AI model for reasoning/generation.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt override

        Returns:
            AI response text or None if unavailable
        """
        if not self.use_ai or not self.ai_available:
            return None

        system = system_prompt or self.get_system_prompt()

        try:
            if self.anthropic_key:
                return self._call_anthropic(prompt, system)
            elif self.openai_key:
                return self._call_openai(prompt, system)
        except Exception as e:
            print(f"AI call failed: {e}")
            return None

        return None

    def _call_anthropic(self, prompt: str, system: str) -> Optional[str]:
        """Call Anthropic Claude API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_key)

            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                system=system,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except ImportError:
            print("Anthropic package not installed")
            return None
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return None

    def _call_openai(self, prompt: str, system: str) -> Optional[str]:
        """Call OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except ImportError:
            print("OpenAI package not installed")
            return None
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from AI response"""
        if not response:
            return None

        # Try to find JSON in the response
        try:
            # Direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object/array in text
        for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
            match = re.search(pattern, response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        return None

    def _log_execution(
        self,
        task: str,
        response: AgentResponse,
        context: Optional[Dict] = None
    ):
        """Log agent execution for history"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task": task,
            "context": context,
            "response": response.to_dict(),
        }
        self.execution_history.append(entry)

        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities"""
        return []

    def can_handle(self, task: str) -> bool:
        """Check if agent can handle the given task"""
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "ai_available": self.ai_available,
            "ai_provider": self.ai_provider if self.ai_available else None,
            "executions": len(self.execution_history),
        }


class AgentRegistry:
    """
    Registry for managing multiple agents.
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        """Register an agent"""
        self._agents[agent.name.lower()] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name"""
        return self._agents.get(name.lower())

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        return [agent.get_status() for agent in self._agents.values()]

    def find_agent_for_task(self, task: str) -> Optional[BaseAgent]:
        """Find the best agent to handle a task"""
        for agent in self._agents.values():
            if agent.can_handle(task):
                return agent
        return None
