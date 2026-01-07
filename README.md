# Agentic AI Marketing Campaign Planner

An open-source, AI-native marketing automation platform that uses autonomous agents to plan, create, and optimize marketing campaigns through natural language.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Overview

Traditional marketing platforms require manual configuration of segments, content, and workflows. This platform takes a fundamentally different approach: **describe what you want in plain English, and AI agents collaborate to make it happen.**

```
> Create a winback campaign for customers who haven't purchased in 30 days

[SegmentationAgent] Created segment "Inactive 30+ Days" with 847 customers
[ContentAgent] Generated personalized email with 20% off incentive
[WorkflowAgent] Designed 3-step re-engagement sequence
[AnalyticsAgent] Predicted 12% reactivation rate based on historical data
```

## Key Features

### Autonomous AI Agents

| Agent | Capabilities |
|-------|-------------|
| **Orchestrator** | Interprets natural language, coordinates all agents |
| **Segmentation Agent** | Discovers audiences, creates segments from descriptions |
| **Content Agent** | Generates email/SMS/push content, A/B variants |
| **Workflow Agent** | Designs multi-step automated campaigns |
| **Analytics Agent** | Predicts churn, recommends actions, analyzes performance |

### Customer Data Platform (CDP)

- **Unified Profiles**: 360° customer view with behavioral data
- **Event Tracking**: Purchases, email opens, page views, custom events
- **Computed Traits**: Automatic calculation of RFM, engagement scores
- **Predictive Scores**: Churn risk, lifetime value, conversion probability

### Campaign Engine

- **Multi-channel**: Email, SMS, Push notifications, Webhooks
- **Workflow Automation**: Conditional branching, wait steps, triggers
- **A/B Testing**: Built-in variant testing framework
- **Personalization**: Dynamic content with customer attributes

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/agentic-ai-marketing.git
cd agentic-ai-marketing

# Install dependencies
pip install -r requirements.txt

# (Optional) Set AI API key for enhanced capabilities
export ANTHROPIC_API_KEY="your-key"
# or
export OPENAI_API_KEY="your-key"
```

### Run with Demo Data

```bash
# Start with 100 sample customers
python main.py --demo

# Start with more data
python main.py --demo -n 500
```

### Interactive Mode

```bash
python main.py
```

## Usage Examples

### Segmentation

```
> Create a segment for high-value customers who spent over $500
> Find customers at risk of churning
> Discover potential audience segments
> Show me customers who opened emails but didn't purchase
```

### Content Generation

```
> Write a welcome email for new subscribers
> Generate SMS for a flash sale ending tonight
> Create 3 A/B variants for a cart abandonment email
> Optimize this subject line: "Check out our new products"
```

### Workflow Automation

```
> Build a 5-step onboarding sequence for new users
> Create a cart abandonment workflow with SMS fallback
> Design a winback campaign for inactive customers
> Show me workflow templates
```

### Analytics & Insights

```
> Show me platform health
> Analyze churn risk across segments
> What campaigns should I run?
> Calculate optimal send times
```

### Full Campaign Creation

```
> Create a holiday promotion campaign targeting repeat buyers
```

This single command will:
1. Create/identify the target segment
2. Generate personalized content
3. Design an appropriate workflow
4. Provide performance predictions

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                           │
│           (Natural Language → Agent Coordination)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
     ▼                     ▼                     ▼
┌──────────┐        ┌─────────────┐       ┌──────────────┐
│SEGMENT   │        │  CONTENT    │       │  WORKFLOW    │
│ AGENT    │        │   AGENT     │       │    AGENT     │
└────┬─────┘        └──────┬──────┘       └──────┬───────┘
     │                     │                     │
     └─────────────────────┼─────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    ANALYTICS AGENT     │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   CUSTOMER DATA        │
              │   PLATFORM (CDP)       │
              └────────────────────────┘
```

## Project Structure

```
agentic_ai_marketing_campaign/
├── main.py                 # CLI entry point
├── config.py               # Configuration
├── requirements.txt        # Dependencies
│
├── cdp/                    # Customer Data Platform
│   ├── customer.py         # Customer profiles
│   ├── events.py           # Event tracking
│   ├── traits.py           # Computed traits
│   ├── storage.py          # SQLite persistence
│   └── ingestion.py        # Data import
│
├── agents/                 # AI Agents
│   ├── base_agent.py       # Base agent framework
│   ├── orchestrator.py     # Master coordinator
│   ├── segmentation_agent.py
│   ├── content_agent.py
│   ├── workflow_agent.py
│   └── analytics_agent.py
│
├── campaigns/              # Campaign Engine
│   ├── campaign.py         # Campaign model
│   ├── workflow.py         # Workflow execution
│   ├── channels.py         # Channel adapters
│   └── executor.py         # Campaign runner
│
├── models/                 # Data Models
│   ├── segment.py          # Segment definitions
│   ├── content.py          # Content templates
│   └── metrics.py          # Analytics models
│
└── data/                   # Sample data
    └── *.json
```

## AI Integration

The platform works in two modes:

### With AI API Keys (Enhanced)
- Natural language understanding for complex requests
- AI-generated content with brand voice
- Intelligent segment discovery
- Predictive recommendations

### Without API Keys (Rule-based)
- Pattern matching for intent detection
- Template-based content generation
- Predefined segment templates
- Heuristic-based predictions

Set your API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# or
export OPENAI_API_KEY="sk-..."
```

## Configuration

Edit `config.py` or use environment variables:

```python
# AI Provider
AI_PROVIDER=anthropic  # or "openai"

# Database
DB_PATH=data/marketing_platform.db

# Campaign Settings
MAX_BATCH_SIZE=1000
DEFAULT_TIMEZONE=UTC
```

## Extending the Platform

### Adding a New Channel

```python
from campaigns.channels import ChannelAdapter, MessageResult

class SlackChannel(ChannelAdapter):
    @property
    def channel_name(self) -> str:
        return "slack"

    def send(self, channel: str, message: str, **kwargs) -> MessageResult:
        # Implementation here
        pass
```

### Adding a New Agent

```python
from agents.base_agent import BaseAgent, AgentResponse

class CustomAgent(BaseAgent):
    def get_system_prompt(self) -> str:
        return "Your agent instructions..."

    def execute(self, task: str, context: dict = None) -> AgentResponse:
        # Implementation here
        pass
```

## Roadmap

- [ ] REST API endpoints
- [ ] Web dashboard UI
- [ ] Real email/SMS provider integrations (SendGrid, Twilio)
- [ ] Advanced ML models for predictions
- [ ] Multi-tenant support
- [ ] Webhook triggers for real-time automation
- [ ] Import/export for migrations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Python and SQLite for simplicity and portability
- AI capabilities powered by Anthropic Claude and OpenAI GPT
- Inspired by the need for more accessible marketing automation

---

**Note**: This is an open-source project for educational and practical use. It is not affiliated with or endorsed by any commercial marketing platform vendor.
