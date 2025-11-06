from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..models.identity import User, UserStatus


class IdentityProvider(ABC):
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def list_users(self, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        pass
    
    @abstractmethod
    async def provision_access(self, user_id: str, resource_id: str, access_level: str) -> bool:
        pass
    
    @abstractmethod
    async def revoke_access(self, user_id: str, resource_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_user_access(self, user_id: str) -> List[Dict[str, Any]]:
        pass


class MockIdentityProvider(IdentityProvider):
    def __init__(self):
        self.users = self._create_mock_users()
        self.access_assignments = {}
    
    def _create_mock_users(self) -> Dict[str, User]:
        return {
            "user001": User(
                user_id="user001",
                username="john.doe",
                email="john.doe@company.com",
                first_name="John",
                last_name="Doe",
                department="Engineering",
                manager_id="mgr001",
                status=UserStatus.ACTIVE,
                hire_date=datetime(2022, 1, 15),
                roles=["Developer", "Team Lead"]
            ),
            "user002": User(
                user_id="user002",
                username="jane.smith",
                email="jane.smith@company.com",
                first_name="Jane",
                last_name="Smith",
                department="Finance",
                manager_id="mgr002",
                status=UserStatus.ACTIVE,
                hire_date=datetime(2021, 6, 1),
                roles=["Financial Analyst"]
            ),
            "user003": User(
                user_id="user003",
                username="bob.wilson",
                email="bob.wilson@company.com",
                first_name="Bob",
                last_name="Wilson",
                department="Security",
                manager_id="mgr003",
                status=UserStatus.ACTIVE,
                hire_date=datetime(2020, 3, 10),
                roles=["Security Analyst", "SIEM Admin"]
            )
        }
    
    async def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)
    
    async def list_users(self, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        users = list(self.users.values())
        if filters:
            if "department" in filters:
                users = [u for u in users if u.department == filters["department"]]
            if "status" in filters:
                users = [u for u in users if u.status == filters["status"]]
        return users
    
    async def provision_access(self, user_id: str, resource_id: str, access_level: str) -> bool:
        if user_id not in self.users:
            return False
        
        if user_id not in self.access_assignments:
            self.access_assignments[user_id] = []
        
        self.access_assignments[user_id].append({
            "resource_id": resource_id,
            "access_level": access_level,
            "granted_at": datetime.now()
        })
        return True
    
    async def revoke_access(self, user_id: str, resource_id: str) -> bool:
        if user_id not in self.access_assignments:
            return False
        
        self.access_assignments[user_id] = [
            a for a in self.access_assignments[user_id] 
            if a["resource_id"] != resource_id
        ]
        return True
    
    async def get_user_access(self, user_id: str) -> List[Dict[str, Any]]:
        return self.access_assignments.get(user_id, [])
