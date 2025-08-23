"""
Slack Integration for Team Alert Notifications
Provides comprehensive team communication and status updates.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Requests library not available, Slack integration will be limited")

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    print("Slack SDK not available, using webhook integration only")


class MessageType(Enum):
    """Slack message types."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationLevel(Enum):
    """Notification urgency levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class SlackConfig:
    """Slack integration configuration."""

    webhook_url: str = ""
    bot_token: str = ""
    default_channel: str = "#alerts"
    mention_users: List[str] = field(default_factory=list)
    mention_groups: List[str] = field(default_factory=list)
    thread_alerts: bool = True

    def __post_init__(self):
        if not self.webhook_url:
            self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        if not self.bot_token:
            self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")


@dataclass
class AlertMessage:
    """Structured alert message for Slack."""

    title: str
    description: str
    severity: str
    service_name: str
    environment: str
    timestamp: datetime = field(default_factory=datetime.now)
    runbook_url: str = ""
    dashboard_url: str = ""
    additional_context: Dict[str, Any] = field(default_factory=dict)

    def to_slack_blocks(self) -> List[Dict[str, Any]]:
        """Convert alert message to Slack block format."""
        # Determine color based on severity
        color_map = {
            "critical": "#FF0000",
            "error": "#FF6B35",
            "warning": "#FFA500",
            "info": "#36C5F0",
        }
        color = color_map.get(self.severity.lower(), "#36C5F0")

        # Build emoji based on severity
        emoji_map = {
            "critical": ":rotating_light:",
            "error": ":x:",
            "warning": ":warning:",
            "info": ":information_source:",
        }
        emoji = emoji_map.get(self.severity.lower(), ":bell:")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {self.title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\n{self.service_name}"},
                    {"type": "mrkdwn", "text": f"*Environment:*\n{self.environment}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{self.severity.upper()}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ],
            },
        ]

        # Add description if provided
        if self.description:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{self.description}",
                    },
                }
            )

        # Add action buttons
        elements = []
        if self.dashboard_url:
            elements.append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Dashboard",
                        "emoji": True,
                    },
                    "url": self.dashboard_url,
                    "style": "primary",
                }
            )

        if self.runbook_url:
            elements.append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Runbook",
                        "emoji": True,
                    },
                    "url": self.runbook_url,
                }
            )

        if elements:
            blocks.append({"type": "actions", "elements": elements})

        # Add additional context if provided
        if self.additional_context:
            context_text = "\n".join(
                [f"*{key}:* {value}" for key, value in self.additional_context.items()]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Additional Context:*\n{context_text}",
                    },
                }
            )

        return blocks


class SlackIntegration:
    """Slack integration for team notifications."""

    def __init__(self, config: SlackConfig = None):
        self.config = config or SlackConfig()
        self.client = None

        if SLACK_SDK_AVAILABLE and self.config.bot_token:
            self.client = WebClient(token=self.config.bot_token)
            self._verify_connection()

    def _verify_connection(self):
        """Verify Slack connection."""
        try:
            if self.client:
                response = self.client.auth_test()
                logging.info(f"Connected to Slack as: {response['user']}")
        except SlackApiError as e:
            logging.error(f"Failed to connect to Slack: {e}")
            self.client = None

    def send_alert(
        self,
        alert: AlertMessage,
        channel: str = None,
        thread_ts: str = None,
        mention_level: NotificationLevel = NotificationLevel.MEDIUM,
    ) -> Optional[Dict[str, Any]]:
        """Send alert message to Slack."""
        channel = channel or self.config.default_channel

        # Build message with mentions based on severity
        mentions = self._build_mentions(alert.severity, mention_level)

        if self.client:
            return self._send_via_api(alert, channel, thread_ts, mentions)
        elif self.config.webhook_url and REQUESTS_AVAILABLE:
            return self._send_via_webhook(alert, channel, mentions)
        else:
            logging.error("No Slack integration method available")
            return None

    def _build_mentions(self, severity: str, mention_level: NotificationLevel) -> str:
        """Build mention string based on severity and configuration."""
        mentions = []

        # Add user mentions for high severity or urgent notifications
        if severity.lower() in ["critical", "error"] or mention_level in [
            NotificationLevel.HIGH,
            NotificationLevel.URGENT,
        ]:
            mentions.extend([f"<@{user}>" for user in self.config.mention_users])

        # Add group mentions for urgent notifications
        if mention_level == NotificationLevel.URGENT:
            mentions.extend(
                [f"<!subteam^{group}>" for group in self.config.mention_groups]
            )

        # Add @here for critical alerts
        if severity.lower() == "critical":
            mentions.append("<!here>")

        return " ".join(mentions)

    def _send_via_api(
        self, alert: AlertMessage, channel: str, thread_ts: str, mentions: str
    ) -> Optional[Dict[str, Any]]:
        """Send message via Slack Web API."""
        try:
            blocks = alert.to_slack_blocks()

            # Add mentions to the first block if any
            if mentions:
                if blocks:
                    blocks[0]["text"][
                        "text"
                    ] = f"{mentions}\n{blocks[0]['text']['text']}"

            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                thread_ts=thread_ts,
                unfurl_links=False,
                unfurl_media=False,
            )

            logging.info(f"Slack message sent to {channel}: {response['ts']}")
            return response.data

        except SlackApiError as e:
            logging.error(f"Failed to send Slack message: {e}")
            return None

    def _send_via_webhook(
        self, alert: AlertMessage, channel: str, mentions: str
    ) -> Optional[Dict[str, Any]]:
        """Send message via Slack webhook."""
        try:
            blocks = alert.to_slack_blocks()

            # Add mentions to the first block if any
            if mentions:
                if blocks:
                    blocks[0]["text"][
                        "text"
                    ] = f"{mentions}\n{blocks[0]['text']['text']}"

            payload = {
                "channel": channel,
                "username": "Universal Platform Monitor",
                "icon_emoji": ":robot_face:",
                "blocks": blocks,
            }

            response = requests.post(self.config.webhook_url, json=payload, timeout=30)
            response.raise_for_status()

            logging.info(f"Slack webhook message sent to {channel}")
            return {"ok": True}

        except Exception as e:
            logging.error(f"Failed to send Slack webhook message: {e}")
            return None

    def send_deployment_notification(
        self,
        service_name: str,
        version: str,
        environment: str,
        status: str = "started",
        deployer: str = "",
        changes: List[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send deployment notification."""
        emoji_map = {
            "started": ":rocket:",
            "completed": ":white_check_mark:",
            "failed": ":x:",
            "rolled_back": ":leftwards_arrow_with_hook:",
        }
        emoji = emoji_map.get(status, ":information_source:")

        title = f"{emoji} Deployment {status.title()}: {service_name} v{version}"
        description = f"Deployment to {environment} environment"

        if deployer:
            description += f" by {deployer}"

        additional_context = {}
        if changes:
            additional_context["Changes"] = "\n".join(changes[:5])  # Limit to 5 changes
            if len(changes) > 5:
                additional_context["Changes"] += f"\n... and {len(changes) - 5} more"

        alert = AlertMessage(
            title=title,
            description=description,
            severity="info",
            service_name=service_name,
            environment=environment,
            additional_context=additional_context,
        )

        return self.send_alert(alert, mention_level=NotificationLevel.LOW)

    def send_slo_violation(
        self,
        service_name: str,
        slo_name: str,
        current_value: float,
        threshold: float,
        environment: str,
        error_budget_remaining: float = None,
    ) -> Optional[Dict[str, Any]]:
        """Send SLO violation notification."""
        title = f":warning: SLO Violation: {slo_name}"
        description = f"Service {service_name} has violated SLO threshold"

        additional_context = {
            "Current Value": f"{current_value:.2f}%",
            "Threshold": f"{threshold:.2f}%",
        }

        if error_budget_remaining is not None:
            additional_context[
                "Error Budget Remaining"
            ] = f"{error_budget_remaining:.2f}%"

        alert = AlertMessage(
            title=title,
            description=description,
            severity="warning",
            service_name=service_name,
            environment=environment,
            additional_context=additional_context,
        )

        return self.send_alert(alert, mention_level=NotificationLevel.MEDIUM)

    def send_recovery_notification(
        self,
        service_name: str,
        incident_description: str,
        environment: str,
        duration: str,
        root_cause: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Send service recovery notification."""
        title = f":white_check_mark: Service Recovered: {service_name}"
        description = f"Service has recovered from: {incident_description}"

        additional_context = {
            "Downtime Duration": duration,
        }

        if root_cause:
            additional_context["Root Cause"] = root_cause

        alert = AlertMessage(
            title=title,
            description=description,
            severity="success",
            service_name=service_name,
            environment=environment,
            additional_context=additional_context,
        )

        return self.send_alert(alert, mention_level=NotificationLevel.LOW)

    def create_incident_channel(
        self, incident_name: str, description: str, invite_users: List[str] = None
    ) -> Optional[str]:
        """Create a dedicated incident channel."""
        if not self.client:
            logging.error("Slack API client not available for channel creation")
            return None

        channel_name = f"incident-{incident_name.lower().replace(' ', '-')}"

        try:
            # Create channel
            response = self.client.conversations_create(
                name=channel_name, is_private=False
            )

            channel_id = response["channel"]["id"]

            # Set channel topic
            self.client.conversations_setTopic(channel=channel_id, topic=description)

            # Invite users if specified
            if invite_users:
                self.client.conversations_invite(channel=channel_id, users=invite_users)

            logging.info(f"Created incident channel: #{channel_name}")
            return channel_name

        except SlackApiError as e:
            logging.error(f"Failed to create incident channel: {e}")
            return None

    def update_channel_status(
        self, channel: str, status: str, details: str = ""
    ) -> bool:
        """Update channel with status information."""
        status_message = f":information_source: **Status Update:** {status}"
        if details:
            status_message += f"\n{details}"

        alert = AlertMessage(
            title="Status Update",
            description=status_message,
            severity="info",
            service_name="System",
            environment="all",
        )

        result = self.send_alert(
            alert, channel=channel, mention_level=NotificationLevel.LOW
        )
        return result is not None


# Global instance
_global_slack = None


def get_slack(config: SlackConfig = None) -> SlackIntegration:
    """Get the global Slack integration instance."""
    global _global_slack
    if _global_slack is None:
        _global_slack = SlackIntegration(config)
    return _global_slack


# Convenience functions
def send_alert_to_slack(
    title: str, description: str, severity: str, service_name: str, environment: str
):
    """Send a simple alert to Slack."""
    slack = get_slack()
    alert = AlertMessage(
        title=title,
        description=description,
        severity=severity,
        service_name=service_name,
        environment=environment,
    )
    return slack.send_alert(alert)


def notify_deployment(
    service_name: str, version: str, environment: str, status: str = "completed"
):
    """Send deployment notification to Slack."""
    slack = get_slack()
    return slack.send_deployment_notification(
        service_name, version, environment, status
    )
