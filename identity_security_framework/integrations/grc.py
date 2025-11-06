from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class GRCProvider(ABC):
    @abstractmethod
    async def check_policy_compliance(self, user_id: str, resource_id: str, access_level: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get_compliance_frameworks(self) -> List[str]:
        pass
    
    @abstractmethod
    async def log_compliance_event(self, event: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def get_risk_policies(self) -> List[Dict[str, Any]]:
        pass


class MockGRCProvider(GRCProvider):
    def __init__(self):
        self.compliance_logs = []
        self.policies = self._create_mock_policies()
    
    def _create_mock_policies(self) -> List[Dict[str, Any]]:
        return [
            {
                "policy_id": "POL001",
                "name": "Segregation of Duties - Finance",
                "description": "Users cannot have both approval and payment roles",
                "frameworks": ["SOX", "GDPR"],
                "rules": {
                    "conflicting_roles": [["Finance_Approver", "Finance_Payment_Processor"]]
                }
            },
            {
                "policy_id": "POL002",
                "name": "Privileged Access Review",
                "description": "Admin access must be reviewed quarterly",
                "frameworks": ["SOX", "ISO27001"],
                "rules": {
                    "review_frequency_days": 90,
                    "applies_to_roles": ["Admin", "SuperUser"]
                }
            },
            {
                "policy_id": "POL003",
                "name": "Data Access Classification",
                "description": "Sensitive data requires additional approval",
                "frameworks": ["GDPR", "HIPAA"],
                "rules": {
                    "sensitive_resources": ["customer_pii", "financial_records", "health_data"],
                    "requires_approval_from": ["Data Protection Officer", "Security Manager"]
                }
            }
        ]
    
    async def check_policy_compliance(self, user_id: str, resource_id: str, access_level: str) -> Dict[str, Any]:
        violations = []
        
        if "admin" in access_level.lower() or "privileged" in resource_id.lower():
            violations.append({
                "policy_id": "POL002",
                "violation": "Privileged access requires additional review",
                "severity": "medium"
            })
        
        if any(sensitive in resource_id.lower() for sensitive in ["pii", "financial", "health"]):
            violations.append({
                "policy_id": "POL003",
                "violation": "Sensitive data access requires DPO approval",
                "severity": "high"
            })
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "checked_at": datetime.now()
        }
    
    async def get_compliance_frameworks(self) -> List[str]:
        return ["SOX", "GDPR", "HIPAA", "ISO27001", "PCI-DSS"]
    
    async def log_compliance_event(self, event: Dict[str, Any]) -> bool:
        event["logged_at"] = datetime.now()
        event["log_id"] = f"LOG{len(self.compliance_logs) + 1:06d}"
        self.compliance_logs.append(event)
        return True
    
    async def get_risk_policies(self) -> List[Dict[str, Any]]:
        return self.policies
