"""
Content Agent

Generates and optimizes marketing content across channels.
Uses AI for content generation with brand consistency.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import re

from .base_agent import BaseAgent, AgentResponse, AgentStatus
from models.content import Content, ContentTemplate, ContentVariant, ContentChannel, ContentType
from models.content import EMAIL_TEMPLATES, SMS_TEMPLATES


class ContentAgent(BaseAgent):
    """
    AI agent for content generation and optimization.

    Capabilities:
    - Generate email, SMS, and push content from prompts
    - Create A/B test variants
    - Optimize subject lines
    - Personalize content
    - Maintain brand voice consistency
    """

    def __init__(self, storage, use_ai: bool = True):
        super().__init__(
            storage=storage,
            name="ContentAgent",
            description="Generates marketing content using AI",
            use_ai=use_ai
        )

        # Brand voice settings (customizable)
        self.brand_voice = {
            "tone": "friendly and professional",
            "style": "conversational",
            "avoid": ["aggressive sales tactics", "all caps", "excessive exclamation marks"],
        }

    def get_system_prompt(self) -> str:
        return f"""You are a marketing content expert AI. You create compelling marketing content that converts.

Brand Voice Guidelines:
- Tone: {self.brand_voice['tone']}
- Style: {self.brand_voice['style']}
- Avoid: {', '.join(self.brand_voice['avoid'])}

When generating content, output JSON:
{{
    "subject": "Email subject line (for email)",
    "preheader": "Preview text (for email)",
    "body": "Main content body",
    "cta_text": "Call to action button text",
    "cta_url": "{{{{cta_url}}}}",
    "reasoning": "Why this content will be effective"
}}

For A/B variants, output:
{{
    "variants": [
        {{
            "name": "Variant A",
            "subject": "...",
            "body": "...",
            "hypothesis": "Why this variant might work"
        }},
        {{
            "name": "Variant B",
            "subject": "...",
            "body": "...",
            "hypothesis": "Why this variant might work"
        }}
    ]
}}

Use personalization tokens: {{{{first_name}}}}, {{{{last_name}}}}, {{{{location}}}}

Tips:
- Subject lines: 6-10 words, create curiosity or urgency
- Email body: Clear value prop, scannable, single CTA
- SMS: Under 160 characters, direct and actionable
"""

    def get_capabilities(self) -> List[str]:
        return [
            "generate_email",
            "generate_sms",
            "generate_push",
            "create_variants",
            "optimize_subject_line",
            "personalize_content",
        ]

    def can_handle(self, task: str) -> bool:
        task_lower = task.lower()
        keywords = ["content", "email", "sms", "push", "write", "generate", "subject line", "copy"]
        return any(kw in task_lower for kw in keywords)

    def execute(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """Execute content generation task"""
        import time
        start_time = time.time()
        self.status = AgentStatus.THINKING
        context = context or {}

        try:
            task_lower = task.lower()

            # Determine channel
            channel = ContentChannel.EMAIL
            if "sms" in task_lower:
                channel = ContentChannel.SMS
            elif "push" in task_lower:
                channel = ContentChannel.PUSH

            # Determine action
            if "variant" in task_lower or "a/b" in task_lower:
                response = self._create_variants(task, channel)
            elif "subject" in task_lower and "optimize" in task_lower:
                subject = context.get("subject", "")
                response = self._optimize_subject_line(subject)
            elif "template" in task_lower:
                template_type = context.get("template_type", "promotional")
                response = self._get_template(template_type, channel)
            else:
                # Default: generate content
                content_type = self._detect_content_type(task)
                response = self._generate_content(task, channel, content_type)

            self.status = AgentStatus.COMPLETED
            response.execution_time_ms = (time.time() - start_time) * 1000
            self._log_execution(task, response, context)
            return response

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResponse(
                success=False,
                message=f"Content generation error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _generate_content(
        self,
        prompt: str,
        channel: ContentChannel,
        content_type: ContentType
    ) -> AgentResponse:
        """Generate content from prompt"""
        self.status = AgentStatus.EXECUTING

        # Try AI generation
        ai_prompt = f"""Generate {channel.value} content for: {prompt}

Content type: {content_type.value}
Channel: {channel.value}

Return the JSON content object."""

        ai_response = self._call_ai(ai_prompt)
        content_data = None

        if ai_response:
            content_data = self._parse_json_response(ai_response)

        # Fallback to templates
        if not content_data:
            content_data = self._generate_from_template(prompt, channel, content_type)

        if not content_data:
            return AgentResponse(
                success=False,
                message="Could not generate content",
                suggestions=["Try being more specific about the campaign goal"]
            )

        # Create content object
        content = Content(
            name=f"{content_type.value.title()} {channel.value.title()}",
            description=prompt,
            channel=channel,
            content_type=content_type,
            subject=content_data.get("subject"),
            preheader=content_data.get("preheader"),
            body=content_data.get("body", ""),
            cta_text=content_data.get("cta_text"),
            cta_url=content_data.get("cta_url"),
            is_ai_generated=bool(ai_response),
            generation_prompt=prompt,
        )

        return AgentResponse(
            success=True,
            message=f"Generated {channel.value} content",
            data={
                "content": content.to_dict(),
            },
            actions_taken=[f"Generated {channel.value} content"],
            reasoning=content_data.get("reasoning", "Based on prompt"),
            confidence=0.85 if ai_response else 0.6
        )

    def _generate_from_template(
        self,
        prompt: str,
        channel: ContentChannel,
        content_type: ContentType
    ) -> Optional[Dict]:
        """Generate content using templates"""
        prompt_lower = prompt.lower()

        # Select appropriate template
        templates = EMAIL_TEMPLATES if channel == ContentChannel.EMAIL else SMS_TEMPLATES

        # Try to match by content type
        template_key = content_type.value
        if template_key in templates:
            template = templates[template_key]
            return {
                "subject": template.subject_template,
                "preheader": template.preheader_template,
                "body": template.body_template,
                "cta_text": template.cta_text_template,
                "cta_url": template.cta_url_template,
            }

        # Try keyword matching
        for key, template in templates.items():
            if key in prompt_lower:
                return {
                    "subject": template.subject_template,
                    "preheader": template.preheader_template,
                    "body": template.body_template,
                    "cta_text": template.cta_text_template,
                    "cta_url": template.cta_url_template,
                }

        # Default promotional template
        if channel == ContentChannel.EMAIL:
            return {
                "subject": "{{first_name}}, check out our latest offer!",
                "preheader": "Exclusive deals just for you",
                "body": """Hi {{first_name}},

We have an exciting offer we think you'll love!

Check it out and let us know what you think.

Best,
The Team""",
                "cta_text": "Shop Now",
                "cta_url": "https://example.com/shop",
            }
        else:  # SMS
            return {
                "body": "{{first_name}}, don't miss our special offer! Shop now: https://example.com"
            }

    def _create_variants(self, prompt: str, channel: ContentChannel) -> AgentResponse:
        """Create A/B test variants"""
        self.status = AgentStatus.EXECUTING

        ai_prompt = f"""Create 2 A/B test variants for {channel.value} content:
{prompt}

Return JSON with 'variants' array containing different approaches."""

        ai_response = self._call_ai(ai_prompt)
        variants_data = None

        if ai_response:
            variants_data = self._parse_json_response(ai_response)

        # Fallback: create variations manually
        if not variants_data or "variants" not in variants_data:
            base_content = self._generate_from_template(
                prompt, channel, ContentType.PROMOTIONAL
            )
            if base_content:
                variants_data = {
                    "variants": [
                        {
                            "name": "Variant A - Direct",
                            "subject": base_content.get("subject", "").replace("check out", "don't miss"),
                            "body": base_content.get("body", ""),
                            "hypothesis": "Direct urgency approach"
                        },
                        {
                            "name": "Variant B - Personal",
                            "subject": "{{first_name}}, we picked this just for you",
                            "body": base_content.get("body", ""),
                            "hypothesis": "Personal recommendation approach"
                        }
                    ]
                }

        if not variants_data:
            return AgentResponse(
                success=False,
                message="Could not create variants"
            )

        # Create content with variants
        content = Content(
            name="A/B Test Content",
            description=prompt,
            channel=channel,
            use_ab_testing=True,
            is_ai_generated=bool(ai_response),
        )

        for i, v in enumerate(variants_data.get("variants", [])):
            variant = ContentVariant(
                name=v.get("name", f"Variant {chr(65+i)}"),
                weight=50.0,
                subject=v.get("subject"),
                body=v.get("body", ""),
            )
            content.add_variant(variant)

        return AgentResponse(
            success=True,
            message=f"Created {len(content.variants)} A/B variants",
            data={
                "content": content.to_dict(),
                "variants": [
                    {
                        "name": v.name,
                        "hypothesis": variants_data["variants"][i].get("hypothesis", "")
                    }
                    for i, v in enumerate(content.variants)
                ]
            },
            actions_taken=["Created A/B test variants"],
        )

    def _optimize_subject_line(self, subject: str) -> AgentResponse:
        """Optimize an email subject line"""
        if not subject:
            return AgentResponse(
                success=False,
                message="No subject line provided to optimize"
            )

        ai_prompt = f"""Optimize this email subject line for higher open rates:
"{subject}"

Provide 3 optimized alternatives with explanations.
Return JSON: {{"alternatives": [{{"subject": "...", "reason": "..."}}]}}"""

        ai_response = self._call_ai(ai_prompt)
        alternatives = []

        if ai_response:
            data = self._parse_json_response(ai_response)
            if data:
                alternatives = data.get("alternatives", [])

        # Fallback optimizations
        if not alternatives:
            alternatives = [
                {
                    "subject": f"{{{{first_name}}}}, {subject.lower()}",
                    "reason": "Added personalization"
                },
                {
                    "subject": re.sub(r'^', '[Limited Time] ', subject),
                    "reason": "Added urgency"
                },
                {
                    "subject": subject[:40] + "..." if len(subject) > 40 else subject,
                    "reason": "Shortened for mobile"
                }
            ]

        return AgentResponse(
            success=True,
            message=f"Generated {len(alternatives)} subject line alternatives",
            data={
                "original": subject,
                "alternatives": alternatives,
            },
            suggestions=["Test different alternatives with A/B testing"]
        )

    def _get_template(self, template_type: str, channel: ContentChannel) -> AgentResponse:
        """Get a content template"""
        templates = EMAIL_TEMPLATES if channel == ContentChannel.EMAIL else SMS_TEMPLATES

        if template_type in templates:
            template = templates[template_type]
            return AgentResponse(
                success=True,
                message=f"Found template: {template.name}",
                data={"template": template.to_dict()}
            )

        # List available templates
        available = list(templates.keys())
        return AgentResponse(
            success=False,
            message=f"Template '{template_type}' not found",
            suggestions=[f"Available templates: {', '.join(available)}"]
        )

    def _detect_content_type(self, prompt: str) -> ContentType:
        """Detect content type from prompt"""
        prompt_lower = prompt.lower()

        type_keywords = {
            ContentType.WELCOME: ["welcome", "onboard", "new user", "new customer"],
            ContentType.WINBACK: ["winback", "win back", "return", "miss you", "come back"],
            ContentType.CART_ABANDONMENT: ["cart", "abandon", "forgot", "left behind"],
            ContentType.TRANSACTIONAL: ["order", "confirm", "receipt", "shipping"],
            ContentType.EDUCATIONAL: ["learn", "guide", "how to", "tips"],
            ContentType.NEWSLETTER: ["newsletter", "update", "news", "weekly"],
        }

        for content_type, keywords in type_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                return content_type

        return ContentType.PROMOTIONAL

    def personalize(self, content: Content, customer) -> Dict[str, str]:
        """Personalize content for a customer"""
        return content.personalize(customer)

    def list_templates(self, channel: ContentChannel = ContentChannel.EMAIL) -> List[Dict]:
        """List available templates"""
        templates = EMAIL_TEMPLATES if channel == ContentChannel.EMAIL else SMS_TEMPLATES
        return [t.to_dict() for t in templates.values()]
