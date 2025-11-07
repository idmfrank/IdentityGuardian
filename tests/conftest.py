import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

msgraph_module = SimpleNamespace(GraphServiceClient=SimpleNamespace)
msgraph_core_module = SimpleNamespace(APIVersion=SimpleNamespace(v1="v1.0"))
sys.modules.setdefault("msgraph", msgraph_module)
sys.modules.setdefault("msgraph.core", msgraph_core_module)
sys.modules.setdefault("msgraph_core", msgraph_core_module)


class _Field:
    def __init__(self, default=None, default_factory=None, **_kwargs):
        self.default = default
        self.default_factory = default_factory


class _BaseSettings:
    def __init__(self, **kwargs):
        cls = self.__class__
        for name, value in cls.__dict__.items():
            if name.startswith("_"):
                continue
            if isinstance(value, _Field):
                if name in kwargs:
                    setattr(self, name, kwargs[name])
                elif value.default_factory is not None:
                    setattr(self, name, value.default_factory())
                else:
                    setattr(self, name, value.default)
            elif not callable(value):
                setattr(self, name, kwargs.get(name, value))
        for name, value in kwargs.items():
            setattr(self, name, value)


class _BaseModel:
    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)

    def model_dump(self):  # pragma: no cover - lightweight helper
        return self.__dict__.copy()

    @classmethod
    def model_validate(cls, data):  # pragma: no cover - minimal constructor helper
        if data is None:
            data = {}
        return cls(**data)


class _AssistantAgent:
    def __init__(self, *args, **kwargs):
        self.model_client = kwargs.get("model_client")


class _TextMessage:
    def __init__(self, content: str = "", source: str = ""):
        self.content = content
        self.source = source


class _ModelClient:
    async def create(self, *_args, **_kwargs):  # pragma: no cover - simple stub
        return SimpleNamespace(content="")


try:  # pragma: no cover - prefer real pydantic when installed
    import pydantic as _real_pydantic  # type: ignore
except Exception:  # pragma: no cover - fallback stub
    class _ValidationError(Exception):
        pass

    pydantic_module = SimpleNamespace(
        Field=_Field,
        BaseModel=_BaseModel,
        ValidationError=_ValidationError,
    )
    sys.modules.setdefault("pydantic", pydantic_module)

try:  # pragma: no cover - prefer real pydantic-settings when installed
    import pydantic_settings as _real_pydantic_settings  # type: ignore
except Exception:  # pragma: no cover - fallback stub
    def _settings_config_dict(**_kwargs):
        return dict(**_kwargs)

    pydantic_settings_module = SimpleNamespace(
        BaseSettings=_BaseSettings,
        SettingsConfigDict=_settings_config_dict,
    )
    sys.modules.setdefault("pydantic_settings", pydantic_settings_module)

autogen_agents = SimpleNamespace(AssistantAgent=_AssistantAgent)
autogen_messages = SimpleNamespace(TextMessage=_TextMessage)
autogen_module = SimpleNamespace(agents=autogen_agents, messages=autogen_messages)

openai_module = SimpleNamespace(OpenAIChatCompletionClient=_ModelClient)
autogen_ext_models = SimpleNamespace(openai=openai_module)
autogen_ext_module = SimpleNamespace(models=autogen_ext_models)
sys.modules.setdefault("autogen_agentchat", autogen_module)
sys.modules.setdefault("autogen_agentchat.agents", autogen_agents)
sys.modules.setdefault("autogen_agentchat.messages", autogen_messages)
sys.modules.setdefault("autogen_ext", autogen_ext_module)
sys.modules.setdefault("autogen_ext.models", autogen_ext_models)
sys.modules.setdefault("autogen_ext.models.openai", openai_module)


class _ClientSession:  # pragma: no cover - minimal stub
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, *_args, **_kwargs):
        return SimpleNamespace(status=200, json=lambda: {})


aiohttp_module = SimpleNamespace(ClientSession=_ClientSession)
sys.modules.setdefault("aiohttp", aiohttp_module)


class _TracerProvider(SimpleNamespace):
    def start_as_current_span(self, *_args, **_kwargs):
        from contextlib import contextmanager

        @contextmanager
        def _noop():
            yield None

        return _noop()


trace_module = SimpleNamespace(
    get_tracer=lambda *_args, **_kwargs: _TracerProvider(),
    Span=SimpleNamespace,
)
export_module = SimpleNamespace(ConsoleSpanExporter=SimpleNamespace, BatchSpanProcessor=SimpleNamespace)
resources_module = SimpleNamespace(Resource=SimpleNamespace)
sdk_trace_module = SimpleNamespace(TracerProvider=_TracerProvider, export=export_module)
sdk_module = SimpleNamespace(trace=sdk_trace_module, resources=resources_module)
opentelemetry_module = SimpleNamespace(trace=trace_module, sdk=sdk_module)
sys.modules.setdefault("opentelemetry", opentelemetry_module)
sys.modules.setdefault("opentelemetry.trace", trace_module)
sys.modules.setdefault("opentelemetry.sdk", sdk_module)
sys.modules.setdefault("opentelemetry.sdk.trace", sdk_trace_module)
sys.modules.setdefault("opentelemetry.sdk.trace.export", export_module)

semconv_http_attributes = SimpleNamespace(
    HTTP_RESPONSE_STATUS_CODE=200,
    HTTP_REQUEST_METHOD="GET",
)
semconv_attributes_module = SimpleNamespace(http_attributes=semconv_http_attributes)
sys.modules.setdefault("opentelemetry.semconv", SimpleNamespace(attributes=semconv_attributes_module))
sys.modules.setdefault("opentelemetry.semconv.attributes", semconv_attributes_module)
sys.modules.setdefault("opentelemetry.semconv.attributes.http_attributes", semconv_http_attributes)
sys.modules.setdefault(
    "opentelemetry.semconv.attributes.url_attributes",
    SimpleNamespace(URL_FULL="https://example.com", URL_SCHEME="https"),
)
sys.modules.setdefault(
    "opentelemetry.semconv.attributes.network_attributes",
    SimpleNamespace(NETWORK_PROTOCOL_NAME="https"),
)
sys.modules.setdefault(
    "opentelemetry.semconv.attributes.server_attributes",
    SimpleNamespace(SERVER_ADDRESS="localhost"),
)
sys.modules.setdefault("opentelemetry.sdk.resources", resources_module)


try:  # pragma: no cover - prefer real FastAPI when installed
    import fastapi as _fastapi  # type: ignore
    import fastapi.security as _fastapi_security  # type: ignore
except Exception:  # pragma: no cover - fallback stub for unit tests
    class _BaseRouter:
        def __init__(self):
            self.routes = []

        def _register(self, func):
            self.routes.append(func)
            return func

        def add_middleware(self, *_args, **_kwargs):
            return None

        def on_event(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

        def exception_handler(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

        def include_router(self, *_args, **_kwargs):
            return None

        def get(self, *_args, **_kwargs):
            return self._register

        def post(self, *_args, **_kwargs):
            return self._register

        def patch(self, *_args, **_kwargs):
            return self._register

        def delete(self, *_args, **_kwargs):
            return self._register

        def middleware(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    class _FastAPI(_BaseRouter):
        def __init__(self, *args, **_kwargs):
            super().__init__()
            self.state = SimpleNamespace()

    class _HTTPException(Exception):
        def __init__(self, status_code: int, detail: str | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    def _depends(call):
        return call

    class _APIRouter(_BaseRouter):
        pass

    class _HTTPAuthorizationCredentials(SimpleNamespace):
        def __init__(self, credentials: str = ""):
            super().__init__(credentials=credentials)

    class _HTTPBearer:
        def __call__(self, *args, **kwargs):
            return None

    def _header(default=None, **_kwargs):  # pragma: no cover - simple stub
        return default

    fastapi_module = SimpleNamespace(
        Depends=_depends,
        FastAPI=_FastAPI,
        APIRouter=_APIRouter,
        HTTPException=_HTTPException,
        Request=SimpleNamespace,
        Header=_header,
    )
    fastapi_security_module = SimpleNamespace(
        HTTPAuthorizationCredentials=_HTTPAuthorizationCredentials,
        HTTPBearer=_HTTPBearer,
    )
    cors_module = SimpleNamespace(CORSMiddleware=lambda *args, **kwargs: None)

    class _JSONResponse(dict):
        def __init__(self, status_code: int = 200, content: dict | None = None):
            super().__init__(content or {})
            self.status_code = status_code

    responses_module = SimpleNamespace(JSONResponse=_JSONResponse)

    sys.modules.setdefault("fastapi.middleware", SimpleNamespace(cors=cors_module))
    sys.modules.setdefault("fastapi.middleware.cors", cors_module)
    sys.modules.setdefault("fastapi.responses", responses_module)

    sys.modules.setdefault("fastapi", fastapi_module)
    sys.modules.setdefault("fastapi.security", fastapi_security_module)


try:  # pragma: no cover - prefer real slowapi when installed
    import slowapi as _slowapi  # type: ignore
except Exception:  # pragma: no cover - fallback stub
    class _Limiter:
        def __init__(self, *args, **_kwargs):
            pass

        def limit(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    slowapi_module = SimpleNamespace(
        Limiter=_Limiter,
        errors=SimpleNamespace(RateLimitExceeded=Exception),
        util=SimpleNamespace(get_remote_address=lambda *_args, **_kwargs: "test"),
    )
    sys.modules.setdefault("slowapi", slowapi_module)
    sys.modules.setdefault("slowapi.errors", slowapi_module.errors)
    sys.modules.setdefault("slowapi.util", slowapi_module.util)


try:  # pragma: no cover - prefer real tenacity when installed
    import tenacity as _tenacity  # type: ignore
except Exception:  # pragma: no cover - fallback stub
    def _retry(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    def _identity(*_args, **_kwargs):
        return None

    tenacity_module = SimpleNamespace(
        retry=_retry,
        stop_after_attempt=_identity,
        wait_exponential=_identity,
    )
    sys.modules.setdefault("tenacity", tenacity_module)


class _SCIMClient:
    def __init__(self, *args, **_kwargs):
        pass


class _SCIMUser(SimpleNamespace):
    pass


class _SCIMGroup(SimpleNamespace):
    pass


sys.modules.setdefault("scim2_client", SimpleNamespace(Client=_SCIMClient))
sys.modules.setdefault("scim2_models", SimpleNamespace(User=_SCIMUser, Group=_SCIMGroup))


def pytest_configure(config):  # pragma: no cover - test harness setup
    config.addinivalue_line("markers", "asyncio: mark test as asynchronous")
