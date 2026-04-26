"""
NeoPulse AI — Alert Manager
============================
Handles alert routing, throttling, and escalation logic.

Design goals:
  - No alert fatigue: identical alerts are suppressed for a cooldown period.
  - Escalation: Watch for 60s → auto-escalates to Critical notification.
  - Pluggable backends: console (default), SMS (Twilio stub), push (FCM stub).
"""

import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional
from enum import Enum


logger = logging.getLogger("neopulse.alerts")


class Severity(str, Enum):
    INFO     = "INFO"
    WATCH    = "WATCH"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    severity: Severity
    message: str
    heart_rate: float
    respiration_rate: float
    timestamp: float = field(default_factory=time.time)
    escalated: bool = False

    def to_json(self) -> str:
        d = asdict(self)
        d["severity"] = self.severity.value
        return json.dumps(d, indent=2)


# ---------------------------------------------------------------------------
# Alert manager
# ---------------------------------------------------------------------------

class AlertManager:
    """
    Manages alert emission with deduplication and escalation.

    Parameters
    ----------
    cooldown_seconds : float
        Minimum seconds between identical severity alerts.
    escalation_window : float
        Seconds a WATCH alert persists before auto-escalating to CRITICAL.
    backends : list of callables
        Each callable receives an Alert object. Add SMS/push backends here.
    """

    def __init__(
        self,
        cooldown_seconds: float = 30.0,
        escalation_window: float = 60.0,
        backends: Optional[list[Callable]] = None,
    ):
        self.cooldown_seconds   = cooldown_seconds
        self.escalation_window  = escalation_window
        self.backends           = backends or [self._console_backend]

        self._last_alert_time: dict[str, float] = {}
        self._watch_start_time: Optional[float] = None
        self.alert_history: list[Alert] = []

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process(self, reading) -> list[Alert]:
        """
        Evaluate a VitalReading and emit alerts as needed.
        Returns list of Alert objects emitted this cycle.
        """
        from neopulse.core.vitals import VitalReading  # avoid circular import
        emitted: list[Alert] = []

        if reading.status == "Normal":
            self._watch_start_time = None
            return emitted

        severity = Severity.WATCH if reading.status == "Watch" else Severity.CRITICAL
        escalated = False

        # Track watch duration for escalation
        if severity == Severity.WATCH:
            if self._watch_start_time is None:
                self._watch_start_time = time.time()
            elif time.time() - self._watch_start_time > self.escalation_window:
                severity  = Severity.CRITICAL
                escalated = True
                logger.warning("Alert escalated from WATCH to CRITICAL after %.0fs", self.escalation_window)
        else:
            self._watch_start_time = None

        # Deduplicate
        key = severity.value
        now = time.time()
        if key in self._last_alert_time:
            if now - self._last_alert_time[key] < self.cooldown_seconds:
                return emitted  # suppressed — still in cooldown

        self._last_alert_time[key] = now

        # Build alerts from reading.alerts list
        for msg in reading.alerts:
            alert = Alert(
                severity=severity,
                message=msg,
                heart_rate=reading.heart_rate,
                respiration_rate=reading.respiration_rate,
                escalated=escalated,
            )
            self.alert_history.append(alert)
            emitted.append(alert)
            for backend in self.backends:
                try:
                    backend(alert)
                except Exception as e:
                    logger.error("Alert backend failed: %s", e)

        return emitted

    # ------------------------------------------------------------------
    # Built-in backends
    # ------------------------------------------------------------------

    @staticmethod
    def _console_backend(alert: Alert) -> None:
        """Print structured alert to console (default backend)."""
        icons = {Severity.INFO: "ℹ", Severity.WATCH: "⚠", Severity.CRITICAL: "🚨"}
        icon = icons.get(alert.severity, "?")
        ts = time.strftime("%H:%M:%S", time.localtime(alert.timestamp))
        print(f"\n{icon} [{ts}] NeoPulse ALERT ({alert.severity.value})")
        print(f"   {alert.message}")
        print(f"   HR: {alert.heart_rate:.0f} bpm  |  RR: {alert.respiration_rate:.0f} brpm")
        if alert.escalated:
            print("   *** ESCALATED — persistent abnormal readings ***")


# ---------------------------------------------------------------------------
# Stub backends (wire up real SDKs for production)
# ---------------------------------------------------------------------------

def twilio_sms_backend(to_number: str, from_number: str, account_sid: str, auth_token: str):
    """
    Returns a backend callable that sends SMS via Twilio.
    Install: pip install twilio
    """
    def _send(alert: Alert):
        if alert.severity == Severity.INFO:
            return  # don't SMS for INFO level
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # client.messages.create(
        #     body=f"NeoPulse {alert.severity.value}: {alert.message}",
        #     from_=from_number, to=to_number
        # )
        logger.info("[Twilio stub] Would SMS: %s → %s", alert.message, to_number)
    return _send


def fcm_push_backend(device_token: str, server_key: str):
    """
    Returns a backend callable that sends FCM push notification.
    Install: pip install firebase-admin
    """
    def _send(alert: Alert):
        # import firebase_admin
        # from firebase_admin import messaging
        # msg = messaging.Message(
        #     notification=messaging.Notification(
        #         title=f"NeoPulse {alert.severity.value}",
        #         body=alert.message,
        #     ),
        #     token=device_token,
        # )
        # messaging.send(msg)
        logger.info("[FCM stub] Would push: %s", alert.message)
    return _send
