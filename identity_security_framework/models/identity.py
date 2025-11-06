from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(BaseModel):
    user_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    department: str
    manager_id: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    hire_date: datetime
    termination_date: Optional[datetime] = None
    roles: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class AccessRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONED = "provisioned"
    FAILED = "failed"


class AccessRequest(BaseModel):
    request_id: str
    user_id: str
    resource_id: str
    resource_type: str
    access_level: str
    business_justification: str
    requested_at: datetime
    requested_by: str
    approvers: List[str] = Field(default_factory=list)
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    risk_score: float = 0.0
    policy_violations: List[str] = Field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    provisioned_at: Optional[datetime] = None


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"
    MODIFIED = "modified"


class AccessReviewItem(BaseModel):
    review_item_id: str
    campaign_id: str
    user_id: str
    resource_id: str
    resource_type: str
    access_level: str
    last_used: Optional[datetime] = None
    assigned_date: datetime
    reviewer_id: str
    status: ReviewStatus = ReviewStatus.PENDING
    recommendation: Optional[str] = None
    risk_score: float = 0.0
    reviewed_at: Optional[datetime] = None
    justification: Optional[str] = None


class ReviewCampaign(BaseModel):
    campaign_id: str
    campaign_name: str
    scope: str
    created_at: datetime
    start_date: datetime
    end_date: datetime
    created_by: str
    review_items: List[AccessReviewItem] = Field(default_factory=list)
    completion_rate: float = 0.0
    status: str = "active"


class LifecycleEventType(str, Enum):
    JOINER = "joiner"
    MOVER = "mover"
    LEAVER = "leaver"


class LifecycleEvent(BaseModel):
    event_id: str
    event_type: LifecycleEventType
    user_id: str
    triggered_at: datetime
    effective_date: datetime
    source: str
    old_department: Optional[str] = None
    new_department: Optional[str] = None
    old_role: Optional[str] = None
    new_role: Optional[str] = None
    provisioning_tasks: List[str] = Field(default_factory=list)
    deprovisioning_tasks: List[str] = Field(default_factory=list)
    status: str = "pending"
    completed_at: Optional[datetime] = None


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IdentityRisk(BaseModel):
    risk_id: str
    user_id: str
    risk_type: str
    risk_level: RiskLevel
    risk_score: float
    detected_at: datetime
    description: str
    indicators: List[str] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)
    status: str = "open"
    resolved_at: Optional[datetime] = None


class SecurityAlert(BaseModel):
    alert_id: str
    alert_type: str
    severity: str
    user_id: str
    detected_at: datetime
    description: str
    indicators: Dict[str, Any] = Field(default_factory=dict)
    recommended_actions: List[str] = Field(default_factory=list)
    status: str = "new"
    investigated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
