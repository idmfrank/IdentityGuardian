from typing import Dict, Any, List
from datetime import datetime
import uuid
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ..models.identity import LifecycleEvent, LifecycleEventType, User, UserStatus
from ..integrations.identity_provider import IdentityProvider
from ..integrations.itsm import ITSMProvider
from ..utils.telemetry import agent_metrics


class LifecycleAgent:
    def __init__(
        self,
        model_client: OpenAIChatCompletionClient,
        identity_provider: IdentityProvider,
        itsm_provider: ITSMProvider
    ):
        self.identity_provider = identity_provider
        self.itsm_provider = itsm_provider
        self.lifecycle_events = {}
        
        system_message = """You are an Identity Lifecycle Management Agent.

Your responsibilities:
1. Manage joiner (new hire) provisioning workflows
2. Handle mover (role change) access updates
3. Process leaver (termination) deprovisioning
4. Automate role-based access assignments
5. Coordinate with HR systems for lifecycle events
6. Ensure timely provisioning and deprovisioning

For JOINERS:
- Provision baseline access based on role and department
- Set up accounts in all required systems
- Assign manager-approved additional access

For MOVERS:
- Identify access changes needed for new role
- Revoke old role-specific access
- Grant new role-specific access
- Update group memberships

For LEAVERS:
- Immediately disable accounts
- Revoke all access
- Archive user data
- Document offboarding completion

Always prioritize security and compliance in lifecycle operations."""

        self.agent = AssistantAgent(
            name="lifecycle_agent",
            model_client=model_client,
            system_message=system_message,
            description="Manages identity lifecycle for joiners, movers, and leavers"
        )
    
    async def process_joiner(
        self,
        user: User,
        start_date: datetime,
        source: str = "hr_system"
    ) -> Dict[str, Any]:
        agent_metrics.record_event("lifecycle_agent", "joiner_event", {
            "user_id": user.user_id,
            "department": user.department
        })
        
        event_id = str(uuid.uuid4())
        
        provisioning_tasks = await self._generate_joiner_tasks(user)
        
        event = LifecycleEvent(
            event_id=event_id,
            event_type=LifecycleEventType.JOINER,
            user_id=user.user_id,
            triggered_at=datetime.now(),
            effective_date=start_date,
            source=source,
            new_department=user.department,
            provisioning_tasks=provisioning_tasks,
            status="in_progress"
        )
        
        self.lifecycle_events[event_id] = event
        
        ticket_id = await self.itsm_provider.create_ticket(
            title=f"New Hire Provisioning: {user.first_name} {user.last_name}",
            description=f"Provision access for new hire in {user.department}",
            category="Provisioning",
            priority="High"
        )
        
        for task in provisioning_tasks:
            if "baseline" in task.lower():
                await self._provision_baseline_access(user)
        
        event.status = "completed"
        event.completed_at = datetime.now()
        
        agent_metrics.record_event("lifecycle_agent", "joiner_completed", {
            "event_id": event_id,
            "tasks_count": len(provisioning_tasks)
        })
        
        return {
            "event_id": event_id,
            "event_type": "joiner",
            "user_id": user.user_id,
            "status": "completed",
            "provisioning_tasks": provisioning_tasks,
            "ticket_id": ticket_id
        }
    
    async def process_mover(
        self,
        user_id: str,
        new_department: str,
        new_role: str,
        effective_date: datetime
    ) -> Dict[str, Any]:
        agent_metrics.record_event("lifecycle_agent", "mover_event", {
            "user_id": user_id,
            "new_department": new_department
        })
        
        user = await self.identity_provider.get_user(user_id)
        if not user:
            return {"success": False, "reason": "User not found"}
        
        event_id = str(uuid.uuid4())
        
        old_access = await self.identity_provider.get_user_access(user_id)
        
        provisioning_tasks = []
        deprovisioning_tasks = []
        
        if user.department != new_department:
            deprovisioning_tasks.append(f"Remove {user.department}-specific access")
            provisioning_tasks.append(f"Grant {new_department}-specific access")
        
        if new_role not in user.roles:
            provisioning_tasks.append(f"Grant {new_role} role access")
            if user.roles:
                deprovisioning_tasks.append(f"Review and remove old role access: {', '.join(user.roles)}")
        
        event = LifecycleEvent(
            event_id=event_id,
            event_type=LifecycleEventType.MOVER,
            user_id=user_id,
            triggered_at=datetime.now(),
            effective_date=effective_date,
            source="hr_system",
            old_department=user.department,
            new_department=new_department,
            old_role=user.roles[0] if user.roles else None,
            new_role=new_role,
            provisioning_tasks=provisioning_tasks,
            deprovisioning_tasks=deprovisioning_tasks,
            status="completed",
            completed_at=datetime.now()
        )
        
        self.lifecycle_events[event_id] = event
        
        ticket_id = await self.itsm_provider.create_ticket(
            title=f"Role Change: {user.username}",
            description=f"User moving from {user.department} to {new_department}",
            category="Access Change",
            priority="Medium"
        )
        
        return {
            "event_id": event_id,
            "event_type": "mover",
            "user_id": user_id,
            "status": "completed",
            "provisioning_tasks": provisioning_tasks,
            "deprovisioning_tasks": deprovisioning_tasks,
            "ticket_id": ticket_id
        }
    
    async def process_leaver(
        self,
        user_id: str,
        termination_date: datetime,
        source: str = "hr_system"
    ) -> Dict[str, Any]:
        agent_metrics.record_event("lifecycle_agent", "leaver_event", {
            "user_id": user_id
        })
        
        user = await self.identity_provider.get_user(user_id)
        if not user:
            return {"success": False, "reason": "User not found"}
        
        event_id = str(uuid.uuid4())
        
        user_access = await self.identity_provider.get_user_access(user_id)
        
        deprovisioning_tasks = [
            "Disable user account immediately",
            "Revoke all system access",
            "Remove from all groups and roles",
            "Archive user mailbox",
            "Transfer owned resources"
        ]
        
        for access in user_access:
            await self.identity_provider.revoke_access(user_id, access["resource_id"])
        
        event = LifecycleEvent(
            event_id=event_id,
            event_type=LifecycleEventType.LEAVER,
            user_id=user_id,
            triggered_at=datetime.now(),
            effective_date=termination_date,
            source=source,
            old_department=user.department,
            deprovisioning_tasks=deprovisioning_tasks,
            status="completed",
            completed_at=datetime.now()
        )
        
        self.lifecycle_events[event_id] = event
        
        ticket_id = await self.itsm_provider.create_ticket(
            title=f"Employee Offboarding: {user.username}",
            description=f"Terminate access for {user.first_name} {user.last_name}",
            category="Deprovisioning",
            priority="Critical"
        )
        
        agent_metrics.record_event("lifecycle_agent", "leaver_completed", {
            "event_id": event_id,
            "access_revoked": len(user_access)
        })
        
        return {
            "event_id": event_id,
            "event_type": "leaver",
            "user_id": user_id,
            "status": "completed",
            "deprovisioning_tasks": deprovisioning_tasks,
            "access_revoked_count": len(user_access),
            "ticket_id": ticket_id
        }
    
    async def _generate_joiner_tasks(self, user: User) -> List[str]:
        tasks = [
            "Create user account in identity provider",
            "Provision baseline access for role",
            "Add to department groups",
            "Setup email and collaboration tools",
            "Grant access to common resources"
        ]
        
        if "engineer" in user.department.lower() or "developer" in ' '.join(user.roles).lower():
            tasks.extend([
                "Grant code repository access",
                "Provision development environment",
                "Add to engineering tools"
            ])
        
        if "finance" in user.department.lower():
            tasks.extend([
                "Grant financial systems access",
                "Setup compliance training"
            ])
        
        return tasks
    
    async def _provision_baseline_access(self, user: User):
        baseline_resources = [
            f"email_system",
            f"collaboration_tools",
            f"{user.department.lower()}_shared_drive"
        ]
        
        for resource in baseline_resources:
            await self.identity_provider.provision_access(
                user.user_id,
                resource,
                "read"
            )
