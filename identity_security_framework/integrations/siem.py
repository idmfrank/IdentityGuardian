from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random


class SIEMProvider(ABC):
    @abstractmethod
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def query_events(self, user_id: str, time_range: int = 24) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def get_user_behavior_baseline(self, user_id: str) -> Dict[str, Any]:
        pass


class MockSIEMProvider(SIEMProvider):
    def __init__(self):
        self.alerts = []
        self.events = {}
    
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        alert["alert_id"] = f"ALERT{len(self.alerts) + 1:04d}"
        alert["timestamp"] = datetime.now()
        self.alerts.append(alert)
        return True
    
    async def query_events(self, user_id: str, time_range: int = 24) -> List[Dict[str, Any]]:
        events = []
        base_time = datetime.now() - timedelta(hours=time_range)
        
        event_types = ["login", "file_access", "api_call", "privilege_escalation", "data_export"]
        
        for i in range(random.randint(5, 15)):
            events.append({
                "event_id": f"EVT{random.randint(10000, 99999)}",
                "user_id": user_id,
                "event_type": random.choice(event_types),
                "timestamp": base_time + timedelta(hours=random.uniform(0, time_range)),
                "source_ip": f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
                "resource": f"resource_{random.randint(1, 100)}"
            })
        
        return sorted(events, key=lambda x: x["timestamp"])
    
    async def get_user_behavior_baseline(self, user_id: str) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "avg_daily_logins": random.randint(2, 5),
            "typical_login_hours": ["08:00-09:00", "13:00-14:00"],
            "typical_locations": ["Office-NY", "Office-SF"],
            "avg_file_access": random.randint(10, 50),
            "baseline_risk_score": random.uniform(0.1, 0.3)
        }
