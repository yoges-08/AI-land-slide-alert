"""SMS & WhatsApp Notification Service for Multi-Hazard Early Warnings.

Supports both real Twilio SMS gateway delivery and offline/demo simulation mode.
Maintains in-memory subscriber list and a circular log of recent dispatched alerts.
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from backend.app.core.config import settings

# In-memory Circular Notification Log (Max 50 items)
_NOTIFICATION_LOG: List[Dict[str, Any]] = [
    {
        "id": "notif-init-1",
        "phone_number": "+91 98765 43210",
        "district": "Wayanad",
        "risk_level": "Critical",
        "risk_score": 88,
        "status": "DEMO_DELIVERED",
        "message": "🚨 LANDSAFE-NER ALERT\nDistrict: Wayanad\nRisk Level: Critical (88%)\nAction: Move to designated NDRF relief shelter\nTime: 14:30 IST\n⚠️ Advisory prediction. Follow NDMA/IMD.",
        "timestamp_ist": "14:30 IST (Demo)",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "notif-init-2",
        "phone_number": "+91 94120 12345",
        "district": "Chamoli",
        "risk_level": "High",
        "risk_score": 72,
        "status": "DEMO_DELIVERED",
        "message": "🚨 LANDSAFE-NER ALERT\nDistrict: Chamoli\nRisk Level: High (72%)\nAction: Avoid hillside roads and riverbanks\nTime: 12:15 IST\n⚠️ Advisory prediction. Follow NDMA/IMD.",
        "timestamp_ist": "12:15 IST (Demo)",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
]

# In-memory Subscriptions list
_SUBSCRIBERS: List[Dict[str, Any]] = [
    {
        "phone_number": "+91 98765 43210",
        "district": "Wayanad",
        "name": "District Disaster Management Cell",
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    },
    {
        "phone_number": "+91 94120 12345",
        "district": "Chamoli",
        "name": "Emergency Relief Warden",
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }
]

def _get_ist_time_str() -> str:
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d %H:%M:%S IST")


def get_notification_log(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns the most recent dispatched notifications."""
    return list(reversed(_NOTIFICATION_LOG))[:limit]


def get_subscribers() -> List[Dict[str, Any]]:
    """Returns all active alert subscribers."""
    return [s for s in _SUBSCRIBERS if s.get("is_active", True)]


def subscribe_phone(phone_number: str, district: Optional[str] = "All Districts", name: Optional[str] = "Citizen") -> Dict[str, Any]:
    """Registers a phone number for hazard alerts."""
    clean_phone = phone_number.strip()
    if not clean_phone.startswith("+"):
        if len(clean_phone) == 10 and clean_phone.isdigit():
            clean_phone = f"+91{clean_phone}"
        else:
            clean_phone = f"+91 {clean_phone}"

    # Check if already subscribed
    existing = next((s for s in _SUBSCRIBERS if s["phone_number"] == clean_phone), None)
    if existing:
        existing["district"] = district or "All Districts"
        existing["name"] = name or existing.get("name", "Citizen")
        existing["is_active"] = True
        return {"status": "updated", "subscriber": existing}

    new_sub = {
        "phone_number": clean_phone,
        "district": district or "All Districts",
        "name": name or "Citizen",
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }
    _SUBSCRIBERS.append(new_sub)
    return {"status": "subscribed", "subscriber": new_sub}


def unsubscribe_phone(phone_number: str) -> bool:
    """Removes or deactivates a subscriber."""
    clean_phone = phone_number.strip()
    for s in _SUBSCRIBERS:
        if clean_phone in s["phone_number"]:
            s["is_active"] = False
            return True
    return False


def send_sms_alert(
    phone_number: str,
    district_name: str,
    risk_level: str,
    risk_score: int,
    recommended_action: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends or simulates an emergency SMS notification.
    """
    time_str = _get_ist_time_str()
    action = recommended_action or (
        "Evacuate to nearest shelter immediately" if risk_score >= 80 else
        "Avoid steep hillside roads and monitor local stream levels"
    )

    message_body = (
        f"🚨 LANDSAFE-NER ALERT\n"
        f"District: {district_name}\n"
        f"Risk Level: {risk_level} ({risk_score}%)\n"
        f"Action: {action}\n"
        f"Time: {time_str}\n"
        f"⚠️ This is an AI prediction. Follow official NDMA/IMD advisories."
    )

    log_entry = {
        "id": f"notif-{int(time.time() * 1000)}",
        "phone_number": phone_number,
        "district": district_name,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "message": message_body,
        "timestamp_ist": time_str,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # If demo mode or Twilio credentials missing, operate in Demo Delivery Mode
    is_demo = (
        settings.NOTIFICATION_DEMO_MODE
        or not settings.TWILIO_ACCOUNT_SID
        or not settings.TWILIO_AUTH_TOKEN
        or not settings.TWILIO_PHONE_NUMBER
    )

    if is_demo:
        log_entry["status"] = "DEMO_DELIVERED"
        log_entry["gateway"] = "In-Memory Simulation (Demo Mode)"
        _append_to_log(log_entry)
        return log_entry

    # Real Twilio API delivery
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        log_entry["status"] = "SENT"
        log_entry["gateway_sid"] = msg.sid
        _append_to_log(log_entry)
        return log_entry
    except Exception as exc:
        log_entry["status"] = "FAILED"
        log_entry["error"] = str(exc)
        _append_to_log(log_entry)
        return log_entry


def send_test_alert(phone_number: str, district: Optional[str] = "Wayanad") -> Dict[str, Any]:
    """Dispatches a sample test alert to verify gateway/demo functioning."""
    return send_sms_alert(
        phone_number=phone_number,
        district_name=district or "Wayanad",
        risk_level="Critical",
        risk_score=85,
        recommended_action="TEST ALERT: Move to high ground if emergency is active."
    )


def broadcast_critical_alert(district_name: str, risk_score: int, risk_level: str = "Critical") -> List[Dict[str, Any]]:
    """Broadcasts alert to all registered subscribers for the district."""
    results = []
    for sub in get_subscribers():
        sub_dist = sub.get("district", "All Districts")
        if sub_dist == "All Districts" or sub_dist.lower() in district_name.lower():
            res = send_sms_alert(
                phone_number=sub["phone_number"],
                district_name=district_name,
                risk_level=risk_level,
                risk_score=risk_score
            )
            results.append(res)
    return results


def _append_to_log(entry: Dict[str, Any]):
    _NOTIFICATION_LOG.append(entry)
    if len(_NOTIFICATION_LOG) > 50:
        _NOTIFICATION_LOG.pop(0)
