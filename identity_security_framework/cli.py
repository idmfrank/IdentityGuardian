import asyncio
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from autogen_ext.models.openai import OpenAIChatCompletionClient
from .config.settings import get_settings
from .agents.coordinator import CoordinatorAgent
from .agents.access_request_agent import AccessRequestAgent
from .agents.access_review_agent import AccessReviewAgent
from .agents.lifecycle_agent import LifecycleAgent
from .agents.monitoring_agent import MonitoringAgent
from .agents.risk_agent import RiskAgent
from .integrations.identity_provider import MockIdentityProvider
from .integrations.itsm import MockITSMProvider
from .integrations.siem import MockSIEMProvider
from .integrations.grc import MockGRCProvider
from .models.identity import User, UserStatus
from .utils.telemetry import setup_logging, agent_metrics


console = Console()


class IdentitySecurityCLI:
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logging(self.settings.log_level)
        
        self.identity_provider = MockIdentityProvider()
        self.itsm_provider = MockITSMProvider()
        self.siem_provider = MockSIEMProvider()
        self.grc_provider = MockGRCProvider()
        
        if not self.settings.openai_api_key:
            console.print("[yellow]Warning: OPENAI_API_KEY not set. Using mock mode.[/yellow]")
            self.mock_mode = True
        else:
            self.mock_mode = False
            self.model_client = OpenAIChatCompletionClient(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key
            )
            
            self.access_request_agent = AccessRequestAgent(
                self.model_client, self.identity_provider, self.itsm_provider, self.grc_provider
            )
            self.access_review_agent = AccessReviewAgent(
                self.model_client, self.identity_provider, self.grc_provider
            )
            self.lifecycle_agent = LifecycleAgent(
                self.model_client, self.identity_provider, self.itsm_provider
            )
            self.monitoring_agent = MonitoringAgent(
                self.model_client, self.identity_provider, self.siem_provider
            )
            self.risk_agent = RiskAgent(
                self.model_client, self.identity_provider, self.grc_provider, self.siem_provider
            )
            
            self.coordinator = CoordinatorAgent(
                self.model_client,
                self.access_request_agent,
                self.access_review_agent,
                self.lifecycle_agent,
                self.monitoring_agent,
                self.risk_agent
            )
    
    def display_banner(self):
        banner = """
╔══════════════════════════════════════════════════════════════╗
║   Identity Security AI Agent Framework                       ║
║   Powered by Microsoft Agent Framework                       ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(Panel(banner, style="bold cyan"))
    
    def display_menu(self):
        table = Table(title="Available Operations", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Operations", style="green")
        
        if not self.mock_mode:
            operations = self.coordinator.get_available_operations()
            for category, ops in operations.items():
                table.add_row(category, ", ".join(ops))
        else:
            table.add_row("Mock Mode", "Limited operations available")
        
        console.print(table)
        console.print("\n[bold]Commands:[/bold]")
        console.print("  1. demo_access_request - Submit an access request")
        console.print("  2. demo_review_campaign - Create an access review campaign")
        console.print("  3. demo_joiner - Process new hire")
        console.print("  4. demo_risk_assessment - Calculate user risk")
        console.print("  5. demo_monitoring - Analyze user behavior")
        console.print("  6. metrics - Show agent metrics")
        console.print("  7. exit - Exit the CLI\n")
    
    async def demo_access_request(self):
        console.print("\n[bold cyan]Demo: Access Request Workflow[/bold cyan]")
        
        result = await self.coordinator.process_request("access_request", {
            "user_id": "user001",
            "resource_id": "financial_records_db",
            "resource_type": "database",
            "access_level": "read",
            "business_justification": "Need to generate quarterly reports"
        })
        
        console.print(f"\n[green]Request ID:[/green] {result.get('request_id')}")
        console.print(f"[green]Status:[/green] {result.get('status')}")
        console.print(f"[green]Risk Score:[/green] {result.get('risk_score'):.2f}")
        console.print(f"[green]Approvers:[/green] {', '.join(result.get('approvers', []))}")
        
        if result.get('policy_violations'):
            console.print(f"[yellow]Policy Violations:[/yellow] {', '.join(result['policy_violations'])}")
        
        console.print(f"\n[bold]AI Recommendation:[/bold]\n{result.get('recommendation', 'N/A')}")
    
    async def demo_review_campaign(self):
        console.print("\n[bold cyan]Demo: Access Review Campaign[/bold cyan]")
        
        result = await self.coordinator.process_request("create_review_campaign", {
            "campaign_name": "Q4 2025 Access Review",
            "scope": "All Active Users",
            "duration_days": 30
        })
        
        console.print(f"\n[green]Campaign ID:[/green] {result.get('campaign_id')}")
        console.print(f"[green]Campaign Name:[/green] {result.get('campaign_name')}")
        console.print(f"[green]Review Items:[/green] {result.get('review_items_count')}")
        console.print(f"[green]Duration:[/green] {result.get('start_date')} to {result.get('end_date')}")
    
    async def demo_joiner(self):
        console.print("\n[bold cyan]Demo: New Hire Onboarding[/bold cyan]")
        
        new_user = User(
            user_id="user999",
            username="alice.new",
            email="alice.new@company.com",
            first_name="Alice",
            last_name="New",
            department="Engineering",
            manager_id="mgr001",
            status=UserStatus.ACTIVE,
            hire_date=datetime.now(),
            roles=["Developer"]
        )
        
        result = await self.coordinator.process_request("joiner", {
            "user": new_user,
            "start_date": datetime.now()
        })
        
        console.print(f"\n[green]Event ID:[/green] {result.get('event_id')}")
        console.print(f"[green]User:[/green] {result.get('user_id')}")
        console.print(f"[green]Status:[/green] {result.get('status')}")
        console.print(f"\n[bold]Provisioning Tasks:[/bold]")
        for task in result.get('provisioning_tasks', []):
            console.print(f"  ✓ {task}")
    
    async def demo_risk_assessment(self):
        console.print("\n[bold cyan]Demo: User Risk Assessment[/bold cyan]")
        
        result = await self.coordinator.process_request("calculate_risk", {
            "user_id": "user001"
        })
        
        console.print(f"\n[green]User:[/green] {result.get('user_id')}")
        console.print(f"[green]Risk Score:[/green] {result.get('risk_score')}")
        console.print(f"[green]Risk Level:[/green] {result.get('risk_level')}")
        
        console.print(f"\n[bold]Risk Factors:[/bold]")
        for factor in result.get('risk_factors', []):
            console.print(f"  • [{factor['severity']}] {factor['description']}")
        
        console.print(f"\n[bold]Remediation Steps:[/bold]")
        for step in result.get('remediation_steps', []):
            console.print(f"  → {step}")
    
    async def demo_monitoring(self):
        console.print("\n[bold cyan]Demo: User Behavior Analysis[/bold cyan]")
        
        result = await self.coordinator.process_request("analyze_behavior", {
            "user_id": "user001"
        })
        
        console.print(f"\n[green]User:[/green] {result.get('user_id')}")
        console.print(f"[green]Anomalies Detected:[/green] {result.get('anomalies_detected', 0)}")
        
        if result.get('anomalies_detected', 0) > 0:
            console.print(f"[green]Alert ID:[/green] {result.get('alert_id')}")
            console.print(f"[green]Risk Level:[/green] {result.get('risk_level')}")
            
            console.print(f"\n[bold]Anomalies:[/bold]")
            for anomaly in result.get('anomalies', []):
                console.print(f"  • [{anomaly['severity']}] {anomaly['description']}")
        else:
            console.print("[green]No anomalies detected - behavior is normal[/green]")
    
    def show_metrics(self):
        console.print("\n[bold cyan]Agent Metrics[/bold cyan]")
        
        metrics = agent_metrics.get_metrics()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan")
        table.add_column("Event Count", style="green")
        table.add_column("Last Event", style="yellow")
        
        for agent_name, events in metrics.items():
            last_event = events[-1] if events else None
            table.add_row(
                agent_name,
                str(len(events)),
                last_event['event_type'] if last_event else "N/A"
            )
        
        console.print(table)
    
    async def run(self):
        self.display_banner()
        
        if self.mock_mode:
            console.print("[yellow]Running in MOCK MODE - set OPENAI_API_KEY to enable full AI features[/yellow]\n")
        
        while True:
            self.display_menu()
            
            choice = console.input("[bold cyan]Enter command: [/bold cyan]").strip()
            
            try:
                if choice == "1":
                    if self.mock_mode:
                        console.print("[red]This feature requires OPENAI_API_KEY[/red]")
                    else:
                        await self.demo_access_request()
                elif choice == "2":
                    if self.mock_mode:
                        console.print("[red]This feature requires OPENAI_API_KEY[/red]")
                    else:
                        await self.demo_review_campaign()
                elif choice == "3":
                    if self.mock_mode:
                        console.print("[red]This feature requires OPENAI_API_KEY[/red]")
                    else:
                        await self.demo_joiner()
                elif choice == "4":
                    if self.mock_mode:
                        console.print("[red]This feature requires OPENAI_API_KEY[/red]")
                    else:
                        await self.demo_risk_assessment()
                elif choice == "5":
                    if self.mock_mode:
                        console.print("[red]This feature requires OPENAI_API_KEY[/red]")
                    else:
                        await self.demo_monitoring()
                elif choice == "6":
                    self.show_metrics()
                elif choice == "7" or choice.lower() == "exit":
                    console.print("\n[cyan]Thank you for using Identity Security Framework![/cyan]")
                    break
                else:
                    console.print("[red]Invalid choice. Please try again.[/red]")
            
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                self.logger.error(f"CLI error: {str(e)}", exc_info=True)
            
            console.input("\n[dim]Press Enter to continue...[/dim]")


def main():
    cli = IdentitySecurityCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
