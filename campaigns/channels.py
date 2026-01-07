"""
Channel Adapters

Interfaces for sending messages through various channels.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class MessageResult:
    """Result of sending a message"""
    success: bool = True
    message_id: str = ""
    channel: str = ""
    recipient: str = ""
    sent_at: datetime = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.sent_at:
            self.sent_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class ChannelAdapter(ABC):
    """
    Base class for channel adapters.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._sent_messages: List[MessageResult] = []

    @abstractmethod
    def send(self, **kwargs) -> MessageResult:
        """Send a message through the channel"""
        pass

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Get channel name"""
        pass

    def get_sent_messages(self) -> List[MessageResult]:
        """Get list of sent messages"""
        return self._sent_messages

    def clear_messages(self):
        """Clear sent messages history"""
        self._sent_messages = []


class EmailChannel(ChannelAdapter):
    """
    Email channel adapter.

    In production, this would integrate with services like:
    - SendGrid
    - Mailgun
    - Amazon SES
    - Postmark
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.from_email = config.get("from_email", "marketing@example.com") if config else "marketing@example.com"
        self.from_name = config.get("from_name", "Marketing Team") if config else "Marketing Team"

    @property
    def channel_name(self) -> str:
        return "email"

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        preheader: Optional[str] = None,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs
    ) -> MessageResult:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body
            preheader: Preview text
            html_body: HTML body (optional)
            reply_to: Reply-to address

        Returns:
            MessageResult with send status
        """
        # In production, this would call the email service API
        # For now, we simulate a successful send

        result = MessageResult(
            success=True,
            channel="email",
            recipient=to,
            metadata={
                "subject": subject,
                "from": f"{self.from_name} <{self.from_email}>",
                "preheader": preheader,
                "body_length": len(body),
            }
        )

        self._sent_messages.append(result)
        print(f"[EMAIL] To: {to} | Subject: {subject}")

        return result


class SMSChannel(ChannelAdapter):
    """
    SMS channel adapter.

    In production, this would integrate with services like:
    - Twilio
    - MessageBird
    - Vonage (Nexmo)
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.from_number = config.get("from_number", "+1234567890") if config else "+1234567890"

    @property
    def channel_name(self) -> str:
        return "sms"

    def send(
        self,
        to: str,
        message: str,
        **kwargs
    ) -> MessageResult:
        """
        Send an SMS.

        Args:
            to: Recipient phone number
            message: SMS message (max 160 chars for single SMS)

        Returns:
            MessageResult with send status
        """
        # Validate message length
        if len(message) > 160:
            # In production, would split into segments
            segments = (len(message) // 160) + 1
        else:
            segments = 1

        result = MessageResult(
            success=True,
            channel="sms",
            recipient=to,
            metadata={
                "from": self.from_number,
                "message_length": len(message),
                "segments": segments,
            }
        )

        self._sent_messages.append(result)
        print(f"[SMS] To: {to} | Message: {message[:50]}...")

        return result


class PushChannel(ChannelAdapter):
    """
    Push notification channel adapter.

    In production, this would integrate with services like:
    - Firebase Cloud Messaging (FCM)
    - Apple Push Notification Service (APNS)
    - OneSignal
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.app_id = config.get("app_id", "default") if config else "default"

    @property
    def channel_name(self) -> str:
        return "push"

    def send(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        **kwargs
    ) -> MessageResult:
        """
        Send a push notification.

        Args:
            device_token: Target device token
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            MessageResult with send status
        """
        result = MessageResult(
            success=True,
            channel="push",
            recipient=device_token,
            metadata={
                "title": title,
                "body": body,
                "data": data or {},
            }
        )

        self._sent_messages.append(result)
        print(f"[PUSH] To: {device_token[:20]}... | Title: {title}")

        return result


class WebhookChannel(ChannelAdapter):
    """
    Webhook channel for external integrations.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    @property
    def channel_name(self) -> str:
        return "webhook"

    def send(
        self,
        url: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict] = None,
        **kwargs
    ) -> MessageResult:
        """
        Send a webhook.

        Args:
            url: Webhook URL
            payload: JSON payload
            method: HTTP method
            headers: Additional headers

        Returns:
            MessageResult with send status
        """
        # In production, would make actual HTTP request
        result = MessageResult(
            success=True,
            channel="webhook",
            recipient=url,
            metadata={
                "method": method,
                "payload_size": len(str(payload)),
            }
        )

        self._sent_messages.append(result)
        print(f"[WEBHOOK] {method} {url}")

        return result


class ChannelManager:
    """
    Manages multiple channel adapters.
    """

    def __init__(self):
        self._channels: Dict[str, ChannelAdapter] = {}

    def register(self, adapter: ChannelAdapter):
        """Register a channel adapter"""
        self._channels[adapter.channel_name] = adapter

    def get(self, channel_name: str) -> Optional[ChannelAdapter]:
        """Get channel adapter by name"""
        return self._channels.get(channel_name)

    def list_channels(self) -> List[str]:
        """List available channels"""
        return list(self._channels.keys())

    def send(self, channel_name: str, **kwargs) -> MessageResult:
        """Send via specified channel"""
        adapter = self.get(channel_name)
        if not adapter:
            return MessageResult(
                success=False,
                channel=channel_name,
                error=f"Channel '{channel_name}' not registered"
            )
        return adapter.send(**kwargs)

    @classmethod
    def create_default(cls) -> "ChannelManager":
        """Create manager with default channels"""
        manager = cls()
        manager.register(EmailChannel())
        manager.register(SMSChannel())
        manager.register(PushChannel())
        manager.register(WebhookChannel())
        return manager
