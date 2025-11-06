import logging
from datetime import datetime
from typing import Dict, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.sdk.resources import Resource


def setup_telemetry(service_name: str = "identity-security-framework"):
    resource = Resource(attributes={
        "service.name": service_name
    })
    
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(__name__)


def setup_logging(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger("identity_security_framework")


class AgentMetrics:
    def __init__(self):
        self.metrics = {}
    
    def record_event(self, agent_name: str, event_type: str, metadata: Dict[str, Any] = None):
        if agent_name not in self.metrics:
            self.metrics[agent_name] = []
        
        self.metrics[agent_name].append({
            "event_type": event_type,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        })
    
    def get_metrics(self, agent_name: str = None):
        if agent_name:
            return self.metrics.get(agent_name, [])
        return self.metrics


agent_metrics = AgentMetrics()
