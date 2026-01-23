#!/usr/bin/env python3
import asyncio
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class HistoryStore:
    def __init__(self, db_path: str = "./data/history.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._cleanup_task: Optional[asyncio.Task] = None

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS port_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gateway_id TEXT NOT NULL,
                    port_id INTEGER NOT NULL,
                    voltage_mv INTEGER,
                    current_ma INTEGER,
                    power_w REAL,
                    protocol INTEGER,
                    temperature INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_port_history_gateway 
                    ON port_history(gateway_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_port_history_time 
                    ON port_history(timestamp);
                
                CREATE TABLE IF NOT EXISTS gateway_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gateway_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_gateway_events_time 
                    ON gateway_events(gateway_id, timestamp);
                
                CREATE TABLE IF NOT EXISTS power_aggregates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gateway_id TEXT NOT NULL,
                    period_type TEXT NOT NULL,
                    period_start DATETIME NOT NULL,
                    total_power_wh REAL,
                    max_power_w REAL,
                    avg_power_w REAL,
                    sample_count INTEGER,
                    UNIQUE(gateway_id, period_type, period_start)
                );
                
                CREATE INDEX IF NOT EXISTS idx_power_aggregates 
                    ON power_aggregates(gateway_id, period_type, period_start);
            ''')
        logger.info(f"History database initialized at {self.db_path}")

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_port_data(self, gateway_id: str, ports: List[Dict[str, Any]]):
        with self._get_conn() as conn:
            for port in ports:
                conn.execute('''
                    INSERT INTO port_history 
                    (gateway_id, port_id, voltage_mv, current_ma, power_w, protocol, temperature)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    gateway_id,
                    port.get("port_id", 0),
                    port.get("voltage", 0),
                    port.get("current", 0),
                    port.get("power", 0.0),
                    port.get("protocol", 0),
                    port.get("temperature", 0)
                ))

    def record_event(self, gateway_id: str, event_type: str, event_data: Any = None):
        with self._get_conn() as conn:
            conn.execute('''
                INSERT INTO gateway_events (gateway_id, event_type, event_data)
                VALUES (?, ?, ?)
            ''', (gateway_id, event_type, json.dumps(event_data) if event_data else None))

    def get_port_history(
        self,
        gateway_id: str,
        port_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        since = datetime.now() - timedelta(hours=hours)
        
        with self._get_conn() as conn:
            if port_id is not None:
                rows = conn.execute('''
                    SELECT * FROM port_history 
                    WHERE gateway_id = ? AND port_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (gateway_id, port_id, since.isoformat(), limit)).fetchall()
            else:
                rows = conn.execute('''
                    SELECT * FROM port_history 
                    WHERE gateway_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (gateway_id, since.isoformat(), limit)).fetchall()
        
        return [dict(row) for row in rows]

    def get_power_stats(self, gateway_id: str, hours: int = 24) -> Dict[str, Any]:
        since = datetime.now() - timedelta(hours=hours)
        
        with self._get_conn() as conn:
            row = conn.execute('''
                SELECT 
                    SUM(power_w) / 3600.0 as total_wh,
                    MAX(power_w) as max_power,
                    AVG(power_w) as avg_power,
                    COUNT(*) as samples
                FROM port_history
                WHERE gateway_id = ? AND timestamp > ?
            ''', (gateway_id, since.isoformat())).fetchone()
        
        return {
            "gateway_id": gateway_id,
            "period_hours": hours,
            "total_wh": round(row["total_wh"] or 0, 2),
            "max_power_w": round(row["max_power"] or 0, 2),
            "avg_power_w": round(row["avg_power"] or 0, 2),
            "sample_count": row["samples"] or 0
        }

    def get_hourly_power(self, gateway_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        since = datetime.now() - timedelta(hours=hours)
        
        with self._get_conn() as conn:
            rows = conn.execute('''
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    SUM(power_w) as total_power,
                    MAX(power_w) as max_power,
                    AVG(power_w) as avg_power,
                    COUNT(*) as samples
                FROM port_history
                WHERE gateway_id = ? AND timestamp > ?
                GROUP BY hour
                ORDER BY hour
            ''', (gateway_id, since.isoformat())).fetchall()
        
        return [dict(row) for row in rows]

    def get_events(
        self,
        gateway_id: str,
        event_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        since = datetime.now() - timedelta(hours=hours)
        
        with self._get_conn() as conn:
            if event_type:
                rows = conn.execute('''
                    SELECT * FROM gateway_events 
                    WHERE gateway_id = ? AND event_type = ? AND timestamp > ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (gateway_id, event_type, since.isoformat(), limit)).fetchall()
            else:
                rows = conn.execute('''
                    SELECT * FROM gateway_events 
                    WHERE gateway_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (gateway_id, since.isoformat(), limit)).fetchall()
        
        result = []
        for row in rows:
            item = dict(row)
            if item.get("event_data"):
                item["event_data"] = json.loads(item["event_data"])
            result.append(item)
        return result

    def cleanup_old_data(self, days: int = 7):
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_conn() as conn:
            conn.execute('DELETE FROM port_history WHERE timestamp < ?', (cutoff.isoformat(),))
            conn.execute('DELETE FROM gateway_events WHERE timestamp < ?', (cutoff.isoformat(),))
        
        logger.info(f"Cleaned up history data older than {days} days")

    async def start_cleanup_task(self, interval_hours: int = 6, retention_days: int = 7):
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_hours * 3600)
                self.cleanup_old_data(retention_days)
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


_history_store: Optional[HistoryStore] = None


def get_history_store(db_path: str = "./data/history.db") -> HistoryStore:
    global _history_store
    if _history_store is None:
        _history_store = HistoryStore(db_path)
    return _history_store
