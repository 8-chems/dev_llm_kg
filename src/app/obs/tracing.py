from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_tracing(service_name: str = "jev-graphrag", env: str = "dev") -> None:
    """Initialize OpenTelemetry tracer provider."""
    provider = TracerProvider()
    if env == "dev":
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)


def get_tracer(name: str):
    return trace.get_tracer(name)
