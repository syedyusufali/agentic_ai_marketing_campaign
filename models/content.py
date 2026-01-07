"""
Content Models

Defines marketing content, templates, and variants for multi-channel campaigns.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import uuid
import re


class ContentChannel(Enum):
    """Supported content channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class ContentType(Enum):
    """Types of content"""
    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    EDUCATIONAL = "educational"
    WINBACK = "winback"
    WELCOME = "welcome"
    CART_ABANDONMENT = "cart_abandonment"
    NEWSLETTER = "newsletter"


@dataclass
class ContentVariant:
    """
    A variant of content for A/B testing.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""  # e.g., "Variant A", "Control"
    weight: float = 50.0  # Percentage of traffic (0-100)

    # Content
    subject: Optional[str] = None  # For email
    preheader: Optional[str] = None  # For email
    body: str = ""
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None

    # Metrics
    sends: int = 0
    opens: int = 0
    clicks: int = 0
    conversions: int = 0

    @property
    def open_rate(self) -> float:
        return (self.opens / self.sends * 100) if self.sends > 0 else 0

    @property
    def click_rate(self) -> float:
        return (self.clicks / self.sends * 100) if self.sends > 0 else 0

    @property
    def conversion_rate(self) -> float:
        return (self.conversions / self.sends * 100) if self.sends > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "weight": self.weight,
            "subject": self.subject,
            "preheader": self.preheader,
            "body": self.body,
            "cta_text": self.cta_text,
            "cta_url": self.cta_url,
            "sends": self.sends,
            "opens": self.opens,
            "clicks": self.clicks,
            "conversions": self.conversions,
        }


@dataclass
class ContentTemplate:
    """
    A reusable content template with placeholders.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    channel: ContentChannel = ContentChannel.EMAIL
    content_type: ContentType = ContentType.PROMOTIONAL

    # Template content with placeholders like {{first_name}}
    subject_template: Optional[str] = None
    preheader_template: Optional[str] = None
    body_template: str = ""
    cta_text_template: Optional[str] = None
    cta_url_template: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_placeholders(self) -> List[str]:
        """Extract all placeholders from templates"""
        all_text = " ".join(filter(None, [
            self.subject_template,
            self.preheader_template,
            self.body_template,
            self.cta_text_template,
            self.cta_url_template,
        ]))
        return list(set(re.findall(r'\{\{(\w+)\}\}', all_text)))

    def render(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Render template with provided data.

        Args:
            data: Dictionary of placeholder values

        Returns:
            Rendered content
        """
        def replace_placeholders(text: Optional[str]) -> Optional[str]:
            if not text:
                return text
            result = text
            for key, value in data.items():
                result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
            return result

        return {
            "subject": replace_placeholders(self.subject_template),
            "preheader": replace_placeholders(self.preheader_template),
            "body": replace_placeholders(self.body_template),
            "cta_text": replace_placeholders(self.cta_text_template),
            "cta_url": replace_placeholders(self.cta_url_template),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "channel": self.channel.value,
            "content_type": self.content_type.value,
            "subject_template": self.subject_template,
            "preheader_template": self.preheader_template,
            "body_template": self.body_template,
            "cta_text_template": self.cta_text_template,
            "cta_url_template": self.cta_url_template,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Content:
    """
    Marketing content for a campaign.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    channel: ContentChannel = ContentChannel.EMAIL
    content_type: ContentType = ContentType.PROMOTIONAL

    # Content
    subject: Optional[str] = None
    preheader: Optional[str] = None
    body: str = ""
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None

    # A/B variants
    variants: List[ContentVariant] = field(default_factory=list)
    use_ab_testing: bool = False

    # Generation metadata
    is_ai_generated: bool = False
    generation_prompt: Optional[str] = None

    # Template reference
    template_id: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_variant(self, variant: ContentVariant):
        """Add an A/B test variant"""
        self.variants.append(variant)
        self.use_ab_testing = True
        self._normalize_variant_weights()

    def _normalize_variant_weights(self):
        """Ensure variant weights sum to 100"""
        if not self.variants:
            return
        total = sum(v.weight for v in self.variants)
        if total > 0:
            for v in self.variants:
                v.weight = (v.weight / total) * 100

    def select_variant(self) -> ContentVariant:
        """
        Select a variant for delivery based on weights.
        Uses weighted random selection.
        """
        import random

        if not self.variants:
            # Return default content as variant
            return ContentVariant(
                name="Default",
                subject=self.subject,
                preheader=self.preheader,
                body=self.body,
                cta_text=self.cta_text,
                cta_url=self.cta_url,
            )

        rand = random.random() * 100
        cumulative = 0
        for variant in self.variants:
            cumulative += variant.weight
            if rand <= cumulative:
                return variant

        return self.variants[-1]

    def get_winning_variant(self) -> Optional[ContentVariant]:
        """Get the best performing variant by conversion rate"""
        if not self.variants:
            return None
        return max(self.variants, key=lambda v: v.conversion_rate)

    def personalize(self, customer) -> Dict[str, str]:
        """
        Personalize content for a specific customer.

        Args:
            customer: CustomerProfile object

        Returns:
            Personalized content dictionary
        """
        data = {
            "first_name": customer.first_name or "there",
            "last_name": customer.last_name or "",
            "full_name": customer.full_name,
            "email": customer.email or "",
            "location": customer.location or "",
        }

        def replace_tokens(text: Optional[str]) -> Optional[str]:
            if not text:
                return text
            result = text
            for key, value in data.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result

        return {
            "subject": replace_tokens(self.subject),
            "preheader": replace_tokens(self.preheader),
            "body": replace_tokens(self.body),
            "cta_text": replace_tokens(self.cta_text),
            "cta_url": replace_tokens(self.cta_url),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "channel": self.channel.value,
            "content_type": self.content_type.value,
            "subject": self.subject,
            "preheader": self.preheader,
            "body": self.body,
            "cta_text": self.cta_text,
            "cta_url": self.cta_url,
            "variants": [v.to_dict() for v in self.variants],
            "use_ab_testing": self.use_ab_testing,
            "is_ai_generated": self.is_ai_generated,
            "generation_prompt": self.generation_prompt,
            "template_id": self.template_id,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# Pre-built templates for common use cases
EMAIL_TEMPLATES = {
    "welcome": ContentTemplate(
        name="Welcome Email",
        description="Welcome new customers",
        channel=ContentChannel.EMAIL,
        content_type=ContentType.WELCOME,
        subject_template="Welcome to our family, {{first_name}}!",
        preheader_template="We're excited to have you here",
        body_template="""Hi {{first_name}},

Welcome! We're thrilled to have you join us.

Here's what you can expect:
- Exclusive deals and offers
- Early access to new products
- Personalized recommendations

Ready to explore? Click below to get started!

Best,
The Team""",
        cta_text_template="Start Shopping",
        cta_url_template="https://example.com/shop",
    ),
    "cart_abandonment": ContentTemplate(
        name="Cart Abandonment",
        description="Remind customers about abandoned carts",
        channel=ContentChannel.EMAIL,
        content_type=ContentType.CART_ABANDONMENT,
        subject_template="{{first_name}}, you forgot something!",
        preheader_template="Your cart is waiting for you",
        body_template="""Hi {{first_name}},

You left some great items in your cart! Don't miss out.

Complete your purchase now and enjoy free shipping on orders over $50.

Best,
The Team""",
        cta_text_template="Complete Your Order",
        cta_url_template="https://example.com/cart",
    ),
    "winback": ContentTemplate(
        name="Win-back Campaign",
        description="Re-engage inactive customers",
        channel=ContentChannel.EMAIL,
        content_type=ContentType.WINBACK,
        subject_template="We miss you, {{first_name}}!",
        preheader_template="Come back for an exclusive offer",
        body_template="""Hi {{first_name}},

It's been a while since we've seen you, and we miss you!

To welcome you back, here's an exclusive 20% off your next purchase.

Use code: WELCOMEBACK

Best,
The Team""",
        cta_text_template="Claim Your Discount",
        cta_url_template="https://example.com/shop?code=WELCOMEBACK",
    ),
}

SMS_TEMPLATES = {
    "flash_sale": ContentTemplate(
        name="Flash Sale SMS",
        description="Urgent flash sale notification",
        channel=ContentChannel.SMS,
        content_type=ContentType.PROMOTIONAL,
        body_template="{{first_name}}, FLASH SALE! 30% off everything for 24 hours only. Shop now: https://example.com/sale",
    ),
    "order_confirmation": ContentTemplate(
        name="Order Confirmation SMS",
        description="Order confirmation message",
        channel=ContentChannel.SMS,
        content_type=ContentType.TRANSACTIONAL,
        body_template="{{first_name}}, your order #{{order_id}} has been confirmed! Track it here: https://example.com/track/{{order_id}}",
    ),
}
