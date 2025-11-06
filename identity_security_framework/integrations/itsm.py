from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime


class ITSMProvider(ABC):
    @abstractmethod
    async def create_ticket(self, title: str, description: str, category: str, priority: str) -> str:
        pass
    
    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        pass


class MockITSMProvider(ITSMProvider):
    def __init__(self):
        self.tickets = {}
        self.ticket_counter = 1000
    
    async def create_ticket(self, title: str, description: str, category: str, priority: str) -> str:
        ticket_id = f"INC{self.ticket_counter}"
        self.ticket_counter += 1
        
        self.tickets[ticket_id] = {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "status": "New",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        return ticket_id
    
    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        return self.tickets.get(ticket_id)
    
    async def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        if ticket_id not in self.tickets:
            return False
        
        self.tickets[ticket_id].update(updates)
        self.tickets[ticket_id]["updated_at"] = datetime.now()
        return True
