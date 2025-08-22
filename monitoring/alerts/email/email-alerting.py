"""
Email Alerting System
Provides comprehensive email notifications for non-critical alerts and status updates.
"""

import json
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("Jinja2 not available, using simple string formatting")

try:
    import boto3

    AWS_SES_AVAILABLE = True
except ImportError:
    AWS_SES_AVAILABLE = False

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


class EmailProvider(Enum):
    """Email service providers."""

    SMTP = "smtp"
    AWS_SES = "aws_ses"
    SENDGRID = "sendgrid"
    GCP_SMTP = "gcp_smtp"


class AlertCategory(Enum):
    """Email alert categories."""

    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    COST = "cost"
    COMPLIANCE = "compliance"


@dataclass
class EmailConfig:
    """Email configuration settings."""

    provider: EmailProvider = EmailProvider.SMTP
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    use_tls: bool = True

    # AWS SES configuration
    aws_region: str = "us-east-1"
    aws_access_key: str = ""
    aws_secret_key: str = ""

    # SendGrid configuration
    sendgrid_api_key: str = ""

    # Email settings
    from_address: str = "alerts@universal-platform.com"
    from_name: str = "Universal Platform Monitoring"
    reply_to: str = ""

    # Template settings
    template_directory: str = "email_templates"
    default_template: str = "alert_notification.html"

    def __post_init__(self):
        # Load from environment variables if not provided
        if not self.smtp_server:
            self.smtp_server = os.getenv("SMTP_SERVER", "")
        if not self.smtp_username:
            self.smtp_username = os.getenv("SMTP_USERNAME", "")
        if not self.smtp_password:
            self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        if not self.aws_access_key:
            self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        if not self.aws_secret_key:
            self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        if not self.sendgrid_api_key:
            self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")


@dataclass
class EmailAlert:
    """Email alert message structure."""

    subject: str
    message: str
    category: AlertCategory
    severity: str
    service_name: str
    environment: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Recipients
    to_addresses: List[str] = field(default_factory=list)
    cc_addresses: List[str] = field(default_factory=list)
    bcc_addresses: List[str] = field(default_factory=list)

    # Content
    html_content: str = ""
    attachments: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    alert_id: str = ""
    correlation_id: str = ""
    runbook_url: str = ""
    dashboard_url: str = ""
    additional_context: Dict[str, Any] = field(default_factory=dict)

    # Delivery options
    high_priority: bool = False
    suppress_duplicates: bool = True
    max_frequency_minutes: int = 60  # Max one email per hour for same alert


@dataclass
class EmailTemplate:
    """Email template definition."""

    name: str
    subject_template: str
    html_template: str
    text_template: str = ""
    category: AlertCategory = AlertCategory.PERFORMANCE
    variables: Dict[str, Any] = field(default_factory=dict)


class EmailDeliveryService:
    """Email delivery service with multiple provider support."""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.template_engine = None

        # Initialize template engine
        if JINJA2_AVAILABLE and os.path.exists(config.template_directory):
            self.template_engine = jinja2.Environment(
                loader=jinja2.FileSystemLoader(config.template_directory),
                autoescape=jinja2.select_autoescape(["html", "xml"]),
            )

        # Initialize cloud service clients
        self.ses_client = None
        self.sendgrid_client = None

        if config.provider == EmailProvider.AWS_SES and AWS_SES_AVAILABLE:
            self._init_aws_ses()
        elif config.provider == EmailProvider.SENDGRID and SENDGRID_AVAILABLE:
            self._init_sendgrid()

    def _init_aws_ses(self):
        """Initialize AWS SES client."""
        try:
            self.ses_client = boto3.client(
                "ses",
                region_name=self.config.aws_region,
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key,
            )
            logging.info("AWS SES client initialized")
        except Exception as e:
            logging.error(f"Failed to initialize AWS SES: {e}")

    def _init_sendgrid(self):
        """Initialize SendGrid client."""
        try:
            self.sendgrid_client = SendGridAPIClient(
                api_key=self.config.sendgrid_api_key
            )
            logging.info("SendGrid client initialized")
        except Exception as e:
            logging.error(f"Failed to initialize SendGrid: {e}")

    def send_email(self, alert: EmailAlert) -> bool:
        """Send email alert using configured provider."""
        try:
            # Render email content
            rendered_content = self._render_email_content(alert)
            if not rendered_content:
                return False

            subject, html_content, text_content = rendered_content

            # Send based on configured provider
            if self.config.provider == EmailProvider.AWS_SES:
                return self._send_via_ses(alert, subject, html_content, text_content)
            elif self.config.provider == EmailProvider.SENDGRID:
                return self._send_via_sendgrid(
                    alert, subject, html_content, text_content
                )
            else:
                return self._send_via_smtp(alert, subject, html_content, text_content)

        except Exception as e:
            logging.error(f"Failed to send email alert: {e}")
            return False

    def _render_email_content(self, alert: EmailAlert) -> Optional[tuple]:
        """Render email content using templates."""
        try:
            # Prepare template variables
            template_vars = {
                "alert": alert,
                "service_name": alert.service_name,
                "environment": alert.environment,
                "severity": alert.severity,
                "timestamp": alert.timestamp,
                "message": alert.message,
                "runbook_url": alert.runbook_url,
                "dashboard_url": alert.dashboard_url,
                "additional_context": alert.additional_context,
                "platform_name": "Universal Platform",
                "year": datetime.now().year,
            }

            if self.template_engine:
                # Use Jinja2 templates
                try:
                    template_name = f"{alert.category.value}_alert.html"
                    template = self.template_engine.get_template(template_name)
                    html_content = template.render(**template_vars)
                except jinja2.TemplateNotFound:
                    # Fall back to default template
                    template = self.template_engine.get_template(
                        self.config.default_template
                    )
                    html_content = template.render(**template_vars)

                # Render subject
                subject_template = jinja2.Template(alert.subject)
                subject = subject_template.render(**template_vars)

                # Generate text version (simplified)
                text_content = self._html_to_text(html_content)

            else:
                # Use simple string formatting
                subject = alert.subject.format(**template_vars)
                html_content = alert.html_content or self._generate_simple_html(alert)
                text_content = alert.message

            return subject, html_content, text_content

        except Exception as e:
            logging.error(f"Failed to render email content: {e}")
            return None

    def _generate_simple_html(self, alert: EmailAlert) -> str:
        """Generate simple HTML content when templates are not available."""
        severity_colors = {
            "critical": "#dc3545",
            "error": "#fd7e14",
            "warning": "#ffc107",
            "info": "#17a2b8",
        }

        color = severity_colors.get(alert.severity.lower(), "#6c757d")

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px; }}
                .content {{ padding: 20px; background-color: #f8f9fa; margin: 10px 0; border-radius: 5px; }}
                .footer {{ font-size: 12px; color: #6c757d; margin-top: 20px; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{alert.subject}</h2>
                <p><strong>Service:</strong> {alert.service_name} | <strong>Environment:</strong> {alert.environment}</p>
                <p><strong>Severity:</strong> {alert.severity.upper()} | <strong>Time:</strong> {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
            </div>
            
            <div class="content">
                <h3>Alert Details</h3>
                <p>{alert.message}</p>
                
                {self._render_additional_context_html(alert.additional_context)}
            </div>
            
            <div class="actions">
        """

        if alert.dashboard_url:
            html += f'<a href="{alert.dashboard_url}" class="button">View Dashboard</a>'

        if alert.runbook_url:
            html += f'<a href="{alert.runbook_url}" class="button">View Runbook</a>'

        html += f"""
            </div>
            
            <div class="footer">
                <p>This alert was generated by Universal Platform Monitoring at {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                <p>Alert ID: {alert.alert_id}</p>
            </div>
        </body>
        </html>
        """

        return html

    def _render_additional_context_html(self, context: Dict[str, Any]) -> str:
        """Render additional context as HTML."""
        if not context:
            return ""

        html = "<h4>Additional Information</h4><ul>"
        for key, value in context.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"

        return html

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text (simplified)."""
        try:
            import re

            # Remove HTML tags
            text = re.sub(r"<[^>]+>", "", html_content)
            # Replace HTML entities
            text = text.replace("&nbsp;", " ").replace("&amp;", "&")
            # Clean up whitespace
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except:
            return "Plain text version not available"

    def _send_via_smtp(
        self, alert: EmailAlert, subject: str, html_content: str, text_content: str
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.from_name} <{self.config.from_address}>"
            msg["To"] = ", ".join(alert.to_addresses)

            if alert.cc_addresses:
                msg["Cc"] = ", ".join(alert.cc_addresses)

            if self.config.reply_to:
                msg["Reply-To"] = self.config.reply_to

            # Set priority if high priority
            if alert.high_priority:
                msg["X-Priority"] = "1"
                msg["X-MSMail-Priority"] = "High"

            # Attach text and HTML parts
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Add attachments
            for attachment in alert.attachments:
                self._add_attachment(msg, attachment)

            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls(context=context)

                if self.config.smtp_username and self.config.smtp_password:
                    server.login(self.config.smtp_username, self.config.smtp_password)

                all_recipients = (
                    alert.to_addresses + alert.cc_addresses + alert.bcc_addresses
                )
                server.send_message(msg, to_addrs=all_recipients)

            logging.info(f"Email sent via SMTP to {len(all_recipients)} recipients")
            return True

        except Exception as e:
            logging.error(f"Failed to send email via SMTP: {e}")
            return False

    def _send_via_ses(
        self, alert: EmailAlert, subject: str, html_content: str, text_content: str
    ) -> bool:
        """Send email via AWS SES."""
        if not self.ses_client:
            logging.error("AWS SES client not initialized")
            return False

        try:
            response = self.ses_client.send_email(
                Source=f"{self.config.from_name} <{self.config.from_address}>",
                Destination={
                    "ToAddresses": alert.to_addresses,
                    "CcAddresses": alert.cc_addresses,
                    "BccAddresses": alert.bcc_addresses,
                },
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text_content, "Charset": "UTF-8"},
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                    },
                },
            )

            logging.info(f"Email sent via AWS SES: {response['MessageId']}")
            return True

        except Exception as e:
            logging.error(f"Failed to send email via AWS SES: {e}")
            return False

    def _send_via_sendgrid(
        self, alert: EmailAlert, subject: str, html_content: str, text_content: str
    ) -> bool:
        """Send email via SendGrid."""
        if not self.sendgrid_client:
            logging.error("SendGrid client not initialized")
            return False

        try:
            message = Mail(
                from_email=f"{self.config.from_name} <{self.config.from_address}>",
                to_emails=alert.to_addresses,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content,
            )

            # Add CC and BCC
            if alert.cc_addresses:
                for cc in alert.cc_addresses:
                    message.add_cc(cc)

            if alert.bcc_addresses:
                for bcc in alert.bcc_addresses:
                    message.add_bcc(bcc)

            response = self.sendgrid_client.send(message)
            logging.info(f"Email sent via SendGrid: {response.status_code}")
            return response.status_code == 202

        except Exception as e:
            logging.error(f"Failed to send email via SendGrid: {e}")
            return False

    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message."""
        try:
            with open(attachment["path"], "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {attachment.get('filename', 'attachment')}",
                )
                msg.attach(part)
        except Exception as e:
            logging.error(f"Failed to add attachment: {e}")


class EmailAlertManager:
    """Manages email alerts with deduplication and rate limiting."""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.delivery_service = EmailDeliveryService(config)
        self.sent_alerts: Dict[str, datetime] = {}  # Alert deduplication
        self.recipient_groups: Dict[str, List[str]] = {}  # Recipient group management

        self._load_recipient_groups()

    def _load_recipient_groups(self):
        """Load recipient groups from configuration."""
        # Default recipient groups
        self.recipient_groups = {
            "platform_team": ["platform-team@universal-platform.com"],
            "security_team": ["security-team@universal-platform.com"],
            "dev_team": ["dev-team@universal-platform.com"],
            "ops_team": ["ops-team@universal-platform.com"],
            "management": ["management@universal-platform.com"],
        }

        # Try to load from environment or config file
        try:
            groups_json = os.getenv("EMAIL_RECIPIENT_GROUPS", "{}")
            custom_groups = json.loads(groups_json)
            self.recipient_groups.update(custom_groups)
        except:
            pass

    def send_alert(self, alert: EmailAlert, recipient_groups: List[str] = None) -> bool:
        """Send alert with deduplication and rate limiting."""
        # Generate alert key for deduplication
        alert_key = f"{alert.service_name}:{alert.category.value}:{alert.severity}:{hash(alert.message)}"

        # Check if we should suppress duplicate
        if alert.suppress_duplicates and alert_key in self.sent_alerts:
            last_sent = self.sent_alerts[alert_key]
            if datetime.utcnow() - last_sent < timedelta(
                minutes=alert.max_frequency_minutes
            ):
                logging.info(f"Suppressing duplicate alert: {alert_key}")
                return (
                    True  # Consider this success since it was intentionally suppressed
                )

        # Add recipient groups
        if recipient_groups:
            for group_name in recipient_groups:
                if group_name in self.recipient_groups:
                    alert.to_addresses.extend(self.recipient_groups[group_name])

        # Remove duplicates
        alert.to_addresses = list(set(alert.to_addresses))

        # Generate alert ID if not provided
        if not alert.alert_id:
            alert.alert_id = f"alert-{int(datetime.utcnow().timestamp())}-{hash(alert_key) % 10000:04d}"

        # Send the alert
        success = self.delivery_service.send_email(alert)

        if success:
            self.sent_alerts[alert_key] = datetime.utcnow()
            logging.info(f"Email alert sent: {alert.alert_id}")

        return success

    def send_performance_alert(
        self,
        service_name: str,
        environment: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        severity: str = "warning",
    ) -> bool:
        """Send performance-related alert."""
        alert = EmailAlert(
            subject=f"Performance Alert: {service_name} - {metric_name}",
            message=f"Service {service_name} in {environment} has {metric_name} of {current_value} exceeding threshold of {threshold}",
            category=AlertCategory.PERFORMANCE,
            severity=severity,
            service_name=service_name,
            environment=environment,
            additional_context={
                "Metric": metric_name,
                "Current Value": str(current_value),
                "Threshold": str(threshold),
                "Deviation": f"{((current_value - threshold) / threshold * 100):+.1f}%",
            },
        )

        return self.send_alert(alert, recipient_groups=["platform_team", "ops_team"])

    def send_deployment_summary(
        self,
        service_name: str,
        version: str,
        environment: str,
        status: str,
        duration: str,
        changes: List[str] = None,
    ) -> bool:
        """Send deployment summary email."""
        status_map = {
            "success": "✅ Successful",
            "failed": "❌ Failed",
            "partial": "⚠️ Partial",
        }

        status_display = status_map.get(status, status)

        alert = EmailAlert(
            subject=f"Deployment Summary: {service_name} v{version} - {status_display}",
            message=f"Deployment of {service_name} version {version} to {environment} completed with status: {status_display}",
            category=AlertCategory.DEPLOYMENT,
            severity="info" if status == "success" else "warning",
            service_name=service_name,
            environment=environment,
            additional_context={
                "Version": version,
                "Duration": duration,
                "Status": status_display,
                "Changes": "\n".join(changes[:10]) if changes else "No changes listed",
            },
        )

        return self.send_alert(alert, recipient_groups=["dev_team", "ops_team"])

    def send_cost_alert(
        self,
        service_name: str,
        environment: str,
        current_cost: float,
        budget: float,
        period: str = "monthly",
    ) -> bool:
        """Send cost-related alert."""
        utilization = (current_cost / budget) * 100
        severity = (
            "critical"
            if utilization > 100
            else "warning"
            if utilization > 80
            else "info"
        )

        alert = EmailAlert(
            subject=f"Cost Alert: {service_name} - {utilization:.1f}% of {period} budget used",
            message=f"Service {service_name} in {environment} has used {utilization:.1f}% of its {period} budget",
            category=AlertCategory.COST,
            severity=severity,
            service_name=service_name,
            environment=environment,
            additional_context={
                "Current Cost": f"${current_cost:.2f}",
                "Budget": f"${budget:.2f}",
                "Utilization": f"{utilization:.1f}%",
                "Period": period.title(),
                "Remaining": f"${max(0, budget - current_cost):.2f}",
            },
        )

        return self.send_alert(alert, recipient_groups=["ops_team", "management"])

    def send_security_alert(
        self,
        service_name: str,
        environment: str,
        security_event: str,
        threat_level: str,
        details: Dict[str, Any] = None,
    ) -> bool:
        """Send security-related alert."""
        alert = EmailAlert(
            subject=f"🚨 Security Alert: {service_name} - {security_event}",
            message=f"Security event detected in {service_name} ({environment}): {security_event}",
            category=AlertCategory.SECURITY,
            severity="critical" if threat_level == "high" else "warning",
            service_name=service_name,
            environment=environment,
            high_priority=True,
            additional_context={
                "Security Event": security_event,
                "Threat Level": threat_level.title(),
                **(details or {}),
            },
        )

        return self.send_alert(alert, recipient_groups=["security_team", "ops_team"])


# Global instance
_global_email_manager = None


def get_email_manager(config: EmailConfig = None) -> EmailAlertManager:
    """Get the global email alert manager instance."""
    global _global_email_manager
    if _global_email_manager is None:
        if config is None:
            config = EmailConfig()
        _global_email_manager = EmailAlertManager(config)
    return _global_email_manager


# Convenience functions
def send_email_alert(
    subject: str,
    message: str,
    service_name: str,
    environment: str,
    severity: str = "info",
):
    """Send a simple email alert."""
    manager = get_email_manager()
    alert = EmailAlert(
        subject=subject,
        message=message,
        category=AlertCategory.PERFORMANCE,
        severity=severity,
        service_name=service_name,
        environment=environment,
    )
    return manager.send_alert(alert)


def send_performance_email(
    service_name: str, environment: str, metric: str, value: float, threshold: float
):
    """Send performance alert email."""
    manager = get_email_manager()
    return manager.send_performance_alert(
        service_name, environment, metric, value, threshold
    )
