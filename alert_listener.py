import os, json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, List
import requests

OREf_ALERTS_URL = os.getenv("OREf_ALERTS_URL", "https://www.oref.org.il/WarningMessages/alert/alerts.json")

def fetch_alerts() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; family-checkin-mvp/0.3)",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.oref.org.il/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    try:
        r = requests.get(OREf_ALERTS_URL, headers=headers, timeout=10)
        r.raise_for_status()
        try:
            return r.json(), None
        except Exception:
            pass
        for enc in ("utf-16-le", "utf-16", "utf-8"):
            try:
                txt = r.content.decode(enc)
                return json.loads(txt), None
            except Exception:
                continue
        return None, "Could not decode alerts feed as JSON"
    except Exception as e:
        return None, str(e)

def extract_alert_items(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, dict) and "alerts" in payload and isinstance(payload["alerts"], list):
        return payload["alerts"]
    if isinstance(payload, dict) and ("data" in payload or "title" in payload):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []

class AlertStateMachine:
    def __init__(self, all_clear_after_seconds: int):
        self.all_clear_after = timedelta(seconds=all_clear_after_seconds)
        self.active_event_started: Optional[datetime] = None
        self.last_alert_at: Optional[datetime] = None

    def ingest(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        now = datetime.utcnow()
        new_alert = len(alerts) > 0
        became_active = False
        became_cleared = False
        if new_alert:
            if self.active_event_started is None:
                self.active_event_started = now
                became_active = True
            self.last_alert_at = now
        if self.active_event_started is not None and self.last_alert_at is not None:
            if now - self.last_alert_at >= self.all_clear_after:
                became_cleared = True
                self.active_event_started = None
                self.last_alert_at = None
        return {"new_alert": new_alert, "became_active": became_active, "became_cleared": became_cleared, "alert_count": len(alerts)}
