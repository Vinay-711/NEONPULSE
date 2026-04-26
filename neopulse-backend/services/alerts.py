import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def dispatch_emergency_alert(file_id: str, hr_bpm: float, rr_bpm: float):
    """
    Mock implementation of a third-party SMS/Email dispatcher.
    In production, this would use the Twilio or SendGrid SDK.
    """
    msg = (
        f"🚨 NEOPULSE EMERGENCY ALERT 🚨\n"
        f"Patient ID: {file_id}\n"
        f"Heart Rate: {hr_bpm:.1f} BPM\n"
        f"Respiratory Rate: {rr_bpm:.1f} br/min\n"
        f"Immediate attention is required."
    )
    
    # Mock dispatch
    logger.info("--------------------------------------------------")
    logger.info("DISPATCHING EXTERNAL ALERT TO EMERGENCY CONTACTS...")
    logger.info(msg)
    logger.info("--------------------------------------------------")
    
    return True
