"""
Alert service for TradingView x Dhan Trading System
Phase 2: Webhook ingestion + idempotency
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from typing import Optional

from ..models.webhook import TradingViewWebhook


class AlertService:
    """Service for managing trading alerts and idempotency"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("ALERT_DB_PATH", "alerts.db")
        self._init_database()
    
    def _init_database(self):
        """Initialize the alerts database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    hash TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def reset_database(self):
        """Reset database for testing - clear all alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM alerts")
                conn.commit()
        except Exception:
            pass
    
    def _compute_hash(self, alert: TradingViewWebhook) -> str:
        """Compute SHA256 hash of alert id + payload for idempotency"""
        # Create a deterministic string representation
        payload = {
            "id": alert.id,
            "symbol": alert.symbol,
            "signal": alert.signal,
            "ts": alert.ts.isoformat()
        }
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()
    
    def is_duplicate(self, alert: TradingViewWebhook) -> bool:
        """Check if alert is a duplicate based on hash"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM alerts WHERE hash = ?",
                    (self._compute_hash(alert),)
                )
                return cursor.fetchone() is not None
        except Exception:
            # If database error, assume not duplicate to be safe
            return False
    
    def store_alert(self, alert: TradingViewWebhook) -> bool:
        """Store alert in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO alerts (id, hash, symbol, signal, timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert.id,
                        self._compute_hash(alert),
                        alert.symbol,
                        alert.signal,
                        alert.ts.isoformat(),
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_alert_count(self) -> int:
        """Get total number of stored alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM alerts")
                return cursor.fetchone()[0]
        except Exception:
            return 0


# Global alert service instance
_alert_service = None


def get_alert_service() -> AlertService:
    """Get alert service instance"""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service


def reset_alert_service():
    """Reset global alert service instance for testing"""
    global _alert_service
    _alert_service = None
