# -*- coding: utf-8 -*-
"""
Gemini-first LLM connector and function-calling router for emotion analysis.

This module intentionally keeps the existing analyzer APIs intact.  The
low-level analyzers still accept an injected ``llm_caller(prompt)`` function,
while this connector provides:

- secret loading for Gemini API keys without printing secret values,
- a Gemini-backed ``llm_caller`` factory, and
- a Gemini Function Calling router that exposes the existing emotion/risk
  analysis functions as tools the model may choose from.

Live Gemini calls require the optional ``google-genai`` package and a configured
``GEMINI_API_KEY``. Unit tests can inject fake callers/clients and never need
network access.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:  # python-dotenv is already a project dependency, but keep import optional.
    from dotenv import dotenv_values
except Exception:  # pragma: no cover - exercised only when dependency is absent.
    dotenv_values = None  # type: ignore[assignment]

from .emotion_analyzer import analyze_dialogue_emotion, analyze_emotion
from .risk_analyzer import analyze_risk, full_analysis

LLMCaller = Callable[[str], str]

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_SECRET_FILENAMES = (
    Path(".streamlit") / "secrets.toml",
    Path("data") / ".env",
    Path(".env"),
)


class GeminiConnectorError(RuntimeError):
    """Raised when the Gemini connector cannot be initialized or invoked."""


@dataclass(frozen=True)
class ToolDispatchResult:
    """Structured result from local tool dispatch."""

    tool_name: str
    result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"tool_name": self.tool_name, "result": self.result}


def _project_root() -> Path:
    """Return the repository root inferred from this file location."""

    # src/emotion/llm_connector.py -> repo root
    return Path(__file__).resolve().parents[2]


def _read_toml_secret(path: Path, key: str, default: str) -> str:
    try:
        try:
            import tomllib
        except ImportError:  # pragma: no cover - Python <3.11 fallback.
            import tomli as tomllib  # type: ignore[no-redef]

        with path.open("rb") as f:
            data = tomllib.load(f)
        value = data.get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return default


def _read_dotenv_secret(path: Path, key: str, default: str) -> str:
    if dotenv_values is None:
        return default
    try:
        value = dotenv_values(path).get(key)
    except Exception:
        return default
    return str(value) if value else default


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip('"').strip("'")
    if not normalized:
        return True
    return (
        normalized.startswith("<")
        or normalized.startswith("your_")
        or normalized.upper() in {"TODO", "TBD", "REPLACE_ME", "CHANGEME"}
    )


def load_secret(
    key: str = "GEMINI_API_KEY",
    default: str = "",
    *,
    project_root: Path | None = None,
    include_streamlit_runtime: bool = True,
) -> str:
    """Load a secret value without logging or exposing it.

    Lookup order:
    1. Streamlit runtime secrets, when Streamlit is available.
    2. ``.streamlit/secrets.toml``.
    3. Environment variable.
    4. ``data/.env``.
    5. Repository-root ``.env``.

    Placeholder values such as ``<your_api_key>`` are treated as missing.
    """

    root = project_root or _project_root()

    if include_streamlit_runtime:
        try:
            import streamlit as st  # type: ignore

            value = st.secrets.get(key, default)
            if value and not _is_placeholder(str(value)):
                return str(value)
        except Exception:
            pass

    secrets_toml = root / DEFAULT_SECRET_FILENAMES[0]
    if secrets_toml.exists():
        value = _read_toml_secret(secrets_toml, key, default)
        if value and not _is_placeholder(value):
            return value

    value = os.environ.get(key, default)
    if value and not _is_placeholder(value):
        return value

    for rel_path in DEFAULT_SECRET_FILENAMES[1:]:
        dotenv_path = root / rel_path
        if dotenv_path.exists():
            value = _read_dotenv_secret(dotenv_path, key, default)
            if value and not _is_placeholder(value):
                return value

    return default


def create_gemini_caller(
    *,
    api_key: str | None = None,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.0,
    client: Any | None = None,
    project_root: Path | None = None,
) -> LLMCaller:
    """Create a Gemini-backed ``llm_caller(prompt)`` for existing analyzers.

    ``client`` may be injected in tests. When omitted, this imports
    ``google-genai`` lazily and creates ``genai.Client(api_key=...)``.
    """

    resolved_key = api_key if api_key is not None else load_secret(
        "GEMINI_API_KEY", project_root=project_root
    )
    if client is None and not resolved_key:
        raise GeminiConnectorError(
            "GEMINI_API_KEY is not configured. Set it in Streamlit secrets, "
            "environment variables, data/.env, or repository .env."
        )

    genai_types = None
    if client is None:
        try:
            from google import genai
            from google.genai import types as genai_types  # type: ignore[assignment]
        except Exception as exc:  # pragma: no cover - depends on optional package.
            raise GeminiConnectorError(
                "google-genai is required for live Gemini calls. "
                "Install the google-genai package."
            ) from exc
        client = genai.Client(api_key=resolved_key)
    else:
        try:
            from google.genai import types as genai_types  # type: ignore[assignment]
        except Exception:
            genai_types = None

    def caller(prompt: str) -> str:
        try:
            config = None
            if genai_types is not None:
                config = genai_types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                )
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise GeminiConnectorError(f"Gemini content generation failed: {exc}") from exc

        text = getattr(response, "text", None)
        if text:
            return str(text).strip()

        raise GeminiConnectorError("Gemini response did not include text content.")

    return caller


class GeminiFunctionCallingRouter:
    """Gemini Function Calling router for emotion/risk analysis tools.

    The router is Gemini-first for live routing, but it keeps local tool dispatch
    public so tests and non-network callers can verify behavior deterministically.
    """

    def __init__(
        self,
        *,
        llm_caller: LLMCaller | None = None,
        api_key: str | None = None,
        model: str = DEFAULT_GEMINI_MODEL,
        temperature: float = 0.0,
        client: Any | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.project_root = project_root
        self._client = client
        self.llm_caller = llm_caller or create_gemini_caller(
            api_key=api_key,
            model=model,
            temperature=temperature,
            client=client,
            project_root=project_root,
        )

    @staticmethod
    def tool_names() -> tuple[str, ...]:
        """Return the tool names exposed to Gemini and local dispatch."""

        return (
            "analyze_single_emotion",
            "analyze_dialogue_emotion",
            "analyze_dialogue_risk",
            "full_dialogue_analysis",
        )

    def dispatch_tool(self, tool_name: str, **kwargs: Any) -> ToolDispatchResult:
        """Execute one analysis tool locally by name.

        This is the same implementation path used by the Gemini-exposed Python
        tool functions, which keeps live and test dispatch behavior aligned.
        """

        if tool_name == "analyze_single_emotion":
            utterance = str(kwargs.get("utterance", ""))
            result = analyze_emotion(utterance, llm_caller=self.llm_caller).to_dict()
        elif tool_name == "analyze_dialogue_emotion":
            utterances = _coerce_utterances(kwargs.get("utterances"))
            dialogue_id = _optional_str(kwargs.get("dialogue_id"))
            result = analyze_dialogue_emotion(
                utterances,
                dialogue_id=dialogue_id,
                llm_caller=self.llm_caller,
            ).to_dict()
        elif tool_name == "analyze_dialogue_risk":
            utterances = _coerce_utterances(kwargs.get("utterances"))
            dialogue_id = _optional_str(kwargs.get("dialogue_id"))
            result = analyze_risk(
                utterances,
                dialogue_id=dialogue_id,
                llm_caller=self.llm_caller,
            ).to_dict()
        elif tool_name == "full_dialogue_analysis":
            utterances = _coerce_utterances(kwargs.get("utterances"))
            dialogue_id = _optional_str(kwargs.get("dialogue_id"))
            result = full_analysis(
                utterances,
                dialogue_id=dialogue_id,
                llm_caller=self.llm_caller,
            )
        else:
            raise ValueError(f"Unknown emotion analysis tool: {tool_name}")

        return ToolDispatchResult(tool_name=tool_name, result=result)

    def _tool_functions(self) -> list[Callable[..., dict[str, Any]]]:
        """Build Python callables for google-genai automatic function calling."""

        def analyze_single_emotion(utterance: str) -> dict[str, Any]:
            """Analyze one utterance and return its emotion classification."""

            return self.dispatch_tool(
                "analyze_single_emotion", utterance=utterance
            ).to_dict()

        def analyze_dialogue_emotion(
            utterances: list[str], dialogue_id: str = ""
        ) -> dict[str, Any]:
            """Analyze a dialogue and return utterance-level emotion flow."""

            return self.dispatch_tool(
                "analyze_dialogue_emotion",
                utterances=utterances,
                dialogue_id=dialogue_id,
            ).to_dict()

        def analyze_dialogue_risk(
            utterances: list[str], dialogue_id: str = ""
        ) -> dict[str, Any]:
            """Analyze conflict risk for a dialogue."""

            return self.dispatch_tool(
                "analyze_dialogue_risk",
                utterances=utterances,
                dialogue_id=dialogue_id,
            ).to_dict()

        def full_dialogue_analysis(
            utterances: list[str], dialogue_id: str = ""
        ) -> dict[str, Any]:
            """Run emotion analysis and risk analysis for a dialogue."""

            return self.dispatch_tool(
                "full_dialogue_analysis",
                utterances=utterances,
                dialogue_id=dialogue_id,
            ).to_dict()

        return [
            analyze_single_emotion,
            analyze_dialogue_emotion,
            analyze_dialogue_risk,
            full_dialogue_analysis,
        ]

    def route(self, request: str) -> str:
        """Ask Gemini to choose and execute the appropriate analysis tool.

        The google-genai Python SDK handles automatic function calling when
        Python functions are passed as tools. The returned text is Gemini's final
        response after any selected tool calls have completed.
        """

        try:
            from google import genai
            from google.genai import types
        except Exception as exc:  # pragma: no cover - depends on optional package.
            raise GeminiConnectorError(
                "google-genai is required for Gemini function-calling routing."
            ) from exc

        api_key = load_secret("GEMINI_API_KEY", project_root=self.project_root)
        if self._client is not None:
            client = self._client
        elif api_key:
            client = genai.Client(api_key=api_key)
        else:
            raise GeminiConnectorError("GEMINI_API_KEY is not configured.")

        config = types.GenerateContentConfig(
            tools=self._tool_functions(),
            temperature=self.temperature,
        )
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=request,
                config=config,
            )
        except Exception as exc:
            raise GeminiConnectorError(f"Gemini function routing failed: {exc}") from exc

        text = getattr(response, "text", None)
        if text:
            return str(text).strip()
        return _safe_json_dump({"message": "Gemini returned no final text."})

    def route_json(self, request: str) -> dict[str, Any]:
        """Route a request and parse the final Gemini response as JSON when possible."""

        text = self.route(request)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {"response": text}


def create_gemini_function_router(**kwargs: Any) -> GeminiFunctionCallingRouter:
    """Factory for a Gemini-first emotion/risk function-calling router."""

    return GeminiFunctionCallingRouter(**kwargs)


def analyze_with_gemini_tools(request: str, **kwargs: Any) -> str:
    """Convenience entrypoint for Gemini function-calling analysis routing."""

    return create_gemini_function_router(**kwargs).route(request)


def _coerce_utterances(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    raise TypeError("utterances must be a string or sequence of strings")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _safe_json_dump(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)
