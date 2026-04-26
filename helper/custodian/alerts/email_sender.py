import logging
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailSender:
    """Daily summary email via SMTP (Gmail app password, Fastmail, ProtonMail Bridge, etc.)."""

    def __init__(self):
        self.recipient = os.environ.get("KEEPSAKE_CUSTODIAN_EMAIL", "")
        self.smtp_host = os.environ.get("KEEPSAKE_SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("KEEPSAKE_SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("KEEPSAKE_SMTP_USER", "")
        self.smtp_password = os.environ.get("KEEPSAKE_SMTP_PASSWORD", "")
        if not all([self.recipient, self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.warning(
                "Email not fully configured — daily summaries will not send. "
                "Set KEEPSAKE_CUSTODIAN_EMAIL, KEEPSAKE_SMTP_HOST, "
                "KEEPSAKE_SMTP_USER, KEEPSAKE_SMTP_PASSWORD."
            )

    @property
    def configured(self) -> bool:
        return bool(
            self.recipient and self.smtp_host and self.smtp_user and self.smtp_password
        )

    def send_daily_summary(self, results: list, date_str: Optional[str] = None) -> bool:
        if not self.configured:
            return False
        date_str = date_str or datetime.now().strftime("%Y-%m-%d")
        body = self._format_summary(results, date_str)
        subject = f"Keepsake Custodian Report — {date_str}"
        return self._send(subject, body)

    # ── formatting ────────────────────────────────────────────────────────────

    def _format_summary(self, results: list, date_str: str) -> str:
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        worst = min(
            (r.severity.value for r in results),
            key=lambda s: severity_order.get(s, 9),
            default="info",
        )

        n_warn = sum(1 for r in results if r.severity.value == "warning")
        n_crit = sum(1 for r in results if r.severity.value == "critical")

        if n_crit > 0:
            overall = f"{n_crit} CRITICAL, {n_warn} warning"
        elif n_warn > 0:
            overall = f"{n_warn} warning, 0 critical"
        else:
            overall = "All checks passed. System healthy."

        lines = [
            f"Keepsake Custodian Report — {date_str}",
            "",
            f"Overall: {overall}",
            "",
        ]

        icons = {"info": "✓", "warning": "⚠", "critical": "✗"}
        for r in results:
            icon = icons.get(r.severity.value, "?")
            lines.append(f"{icon} {r.check_name:<22} {r.summary}")
            if r.auto_action:
                lines.append(f"  → Auto-action: {r.auto_action}")

        lines += ["", "— Custodian"]
        return "\n".join(lines)

    # ── transport ─────────────────────────────────────────────────────────────

    def _send(self, subject: str, body: str) -> bool:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = self.recipient
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self.smtp_user, self.smtp_password)
                smtp.sendmail(self.smtp_user, [self.recipient], msg.as_string())
            logger.info("Daily summary sent to %s", self.recipient)
            return True
        except Exception as exc:
            logger.error("Email send failed: %s", exc)
            return False
