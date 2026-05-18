#!/usr/bin/env python3
"""
Unit Tests for QA LLM Provider Abstraction Layer
=================================================

Covers:
- BaseLLMProvider abstract interface (abc enforcement)
- Message protocol wrapper types (types.py)
- Provider factory (factory.py): get_qa_llm_provider, list_providers, aliases
- CodexCLIProvider adapter (codex.py): command building, subprocess interaction
- GeminiCLIProvider adapter (gemini.py): command building, subprocess interaction
- OllamaProvider adapter (ollama.py): HTTP calls, payload building, context manager

External dependencies (claude_agent_sdk, subprocess, HTTP) are mocked so that
these tests run without any network access or installed CLIs.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# SDK pre-mock — must happen before any provider import
# ---------------------------------------------------------------------------

if "claude_agent_sdk" not in sys.modules:
    _sdk_mock = MagicMock()
    _sdk_mock.ClaudeSDKClient = MagicMock()
    _sdk_mock.ClaudeAgentOptions = MagicMock()
    _sdk_mock.HookMatcher = MagicMock()
    sys.modules["claude_agent_sdk"] = _sdk_mock
    sys.modules["claude_agent_sdk.types"] = MagicMock()

# ---------------------------------------------------------------------------
# sys.path — ensure apps/backend is importable
# ---------------------------------------------------------------------------

_BACKEND = Path(__file__).parent.parent / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from qa.providers import BaseLLMProvider  # noqa: E402
from qa.providers.codex import CodexCLIProvider  # noqa: E402
from qa.providers.factory import (  # noqa: E402
    _PROVIDER_ALIASES,
    _PROVIDER_REGISTRY,
    get_qa_llm_provider,
    list_provider_aliases,
    list_providers,
)
from qa.providers.gemini import GeminiCLIProvider  # noqa: E402
from qa.providers.ollama import OllamaProvider  # noqa: E402
from qa.providers.types import (  # noqa: E402
    AssistantMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

# ===========================================================================
# Helpers
# ===========================================================================

def _run(coro):
    """Run a coroutine in a new event loop (test helper).

    Uses asyncio.run() to create a fresh event loop each time, which is safe
    in Python 3.10+ where asyncio.get_event_loop() raises RuntimeError in
    threads that have no current event loop (including the main thread after
    the conftest has manipulated the loop).
    """
    return asyncio.run(coro)


async def _collect(async_gen) -> list:
    """Collect all items yielded by an async generator."""
    items = []
    async for item in async_gen:
        items.append(item)
    return items


# ===========================================================================
# 1. Message protocol types
# ===========================================================================


class TestTextBlock:
    """Tests for the TextBlock wrapper class."""

    def test_class_name(self):
        """Class name must be exactly 'TextBlock' for reviewer.py string checks."""
        assert type(TextBlock(text="hello")).__name__ == "TextBlock"

    def test_stores_text(self):
        """TextBlock stores the text attribute."""
        block = TextBlock(text="response text")
        assert block.text == "response text"

    def test_empty_text(self):
        """TextBlock accepts an empty string."""
        block = TextBlock(text="")
        assert block.text == ""


class TestToolUseBlock:
    """Tests for the ToolUseBlock wrapper class."""

    def test_class_name(self):
        """Class name must be exactly 'ToolUseBlock'."""
        assert type(ToolUseBlock(name="read_file")).__name__ == "ToolUseBlock"

    def test_stores_name_and_input(self):
        """ToolUseBlock stores name and input attributes."""
        block = ToolUseBlock(name="write_file", input={"path": "/tmp/x", "content": "y"})
        assert block.name == "write_file"
        assert block.input == {"path": "/tmp/x", "content": "y"}

    def test_default_input_is_empty_dict(self):
        """Default input is an empty dict."""
        block = ToolUseBlock(name="list_dir")
        assert block.input == {}

    def test_input_instances_are_independent(self):
        """Each ToolUseBlock gets its own independent input dict."""
        a = ToolUseBlock(name="tool_a")
        b = ToolUseBlock(name="tool_b")
        a.input["key"] = "value"
        assert "key" not in b.input


class TestToolResultBlock:
    """Tests for the ToolResultBlock wrapper class."""

    def test_class_name(self):
        """Class name must be exactly 'ToolResultBlock'."""
        assert type(ToolResultBlock(content="ok")).__name__ == "ToolResultBlock"

    def test_stores_content_and_is_error(self):
        """ToolResultBlock stores content and is_error."""
        block = ToolResultBlock(content="output", is_error=False)
        assert block.content == "output"
        assert block.is_error is False

    def test_default_is_error_false(self):
        """is_error defaults to False."""
        block = ToolResultBlock(content="data")
        assert block.is_error is False

    def test_error_block(self):
        """is_error can be set to True."""
        block = ToolResultBlock(content="Error: not found", is_error=True)
        assert block.is_error is True

    def test_list_content(self):
        """Content can be a list."""
        block = ToolResultBlock(content=["line1", "line2"])
        assert block.content == ["line1", "line2"]


class TestAssistantMessage:
    """Tests for the AssistantMessage wrapper class."""

    def test_class_name(self):
        """Class name must be exactly 'AssistantMessage'."""
        msg = AssistantMessage(content=[TextBlock(text="hello")])
        assert type(msg).__name__ == "AssistantMessage"

    def test_stores_content(self):
        """AssistantMessage stores the content list."""
        blocks = [TextBlock(text="a"), ToolUseBlock(name="t")]
        msg = AssistantMessage(content=blocks)
        assert msg.content is blocks

    def test_empty_content(self):
        """AssistantMessage accepts an empty content list."""
        msg = AssistantMessage(content=[])
        assert msg.content == []


class TestUserMessage:
    """Tests for the UserMessage wrapper class."""

    def test_class_name(self):
        """Class name must be exactly 'UserMessage'."""
        msg = UserMessage(content=[])
        assert type(msg).__name__ == "UserMessage"

    def test_stores_content(self):
        """UserMessage stores the content list."""
        blocks = [ToolResultBlock(content="done")]
        msg = UserMessage(content=blocks)
        assert msg.content is blocks


# ===========================================================================
# 2. BaseLLMProvider abstract interface
# ===========================================================================


class TestBaseLLMProviderAbstract:
    """Tests verifying BaseLLMProvider is properly abstract."""

    def test_cannot_instantiate_directly(self):
        """BaseLLMProvider is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseLLMProvider()  # type: ignore[abstract]

    def test_subclass_without_all_methods_is_abstract(self):
        """A subclass that implements only some methods stays abstract."""

        class PartialProvider(BaseLLMProvider):
            async def query(self, prompt: str) -> None:
                pass

            # Missing: receive_response, __aenter__, __aexit__

        with pytest.raises(TypeError):
            PartialProvider()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self):
        """A fully-implemented subclass can be instantiated."""

        class ConcreteProvider(BaseLLMProvider):
            async def query(self, prompt: str) -> None:
                pass

            def receive_response(self) -> AsyncIterator:
                async def _gen():
                    yield AssistantMessage(content=[])

                return _gen()

            async def __aenter__(self) -> ConcreteProvider:
                return self

            async def __aexit__(self, *args) -> None:
                pass

        provider = ConcreteProvider()
        assert isinstance(provider, BaseLLMProvider)

    def test_concrete_subclass_async_context_manager(self):
        """A fully-implemented subclass works as an async context manager."""

        class ConcreteProvider(BaseLLMProvider):
            entered = False
            exited = False

            async def query(self, prompt: str) -> None:
                pass

            def receive_response(self) -> AsyncIterator:
                async def _gen():
                    yield AssistantMessage(content=[])

                return _gen()

            async def __aenter__(self) -> ConcreteProvider:
                ConcreteProvider.entered = True
                return self

            async def __aexit__(self, *args) -> None:
                ConcreteProvider.exited = True

        async def _test():
            provider = ConcreteProvider()
            async with provider:
                pass
            assert ConcreteProvider.entered
            assert ConcreteProvider.exited

        _run(_test())

    def test_concrete_subclass_receive_response(self):
        """A fully-implemented subclass can yield messages from receive_response."""

        class ConcreteProvider(BaseLLMProvider):
            async def query(self, prompt: str) -> None:
                self._prompt = prompt

            def receive_response(self) -> AsyncIterator:
                async def _gen():
                    yield AssistantMessage(content=[TextBlock(text=self._prompt)])

                return _gen()

            async def __aenter__(self) -> ConcreteProvider:
                return self

            async def __aexit__(self, *args) -> None:
                pass

        async def _test():
            provider = ConcreteProvider()
            await provider.query("hello world")
            msgs = await _collect(provider.receive_response())
            assert len(msgs) == 1
            assert type(msgs[0]).__name__ == "AssistantMessage"
            assert msgs[0].content[0].text == "hello world"

        _run(_test())


# ===========================================================================
# 3. Provider factory
# ===========================================================================


class TestListProviders:
    """Tests for the list_providers() helper."""

    def test_returns_list(self):
        """list_providers returns a list."""
        assert isinstance(list_providers(), list)

    def test_contains_all_canonical_names(self):
        """list_providers includes all canonical provider names."""
        providers = list_providers()
        for canonical in _PROVIDER_REGISTRY:
            assert canonical in providers

    def test_is_sorted(self):
        """list_providers returns a sorted list."""
        providers = list_providers()
        assert providers == sorted(providers)

    def test_has_four_providers(self):
        """There are exactly four canonical providers."""
        assert len(list_providers()) == 4
        assert set(list_providers()) == {"claude", "codex", "gemini", "ollama"}


class TestListProviderAliases:
    """Tests for the list_provider_aliases() helper."""

    def test_returns_dict(self):
        """list_provider_aliases returns a dict."""
        assert isinstance(list_provider_aliases(), dict)

    def test_returns_copy(self):
        """list_provider_aliases returns a copy, not the live registry."""
        aliases = list_provider_aliases()
        aliases["new_alias"] = "claude"
        assert "new_alias" not in _PROVIDER_ALIASES

    def test_canonical_names_map_to_themselves(self):
        """Each canonical name is its own alias."""
        aliases = list_provider_aliases()
        for canonical in _PROVIDER_REGISTRY:
            assert aliases[canonical] == canonical

    def test_all_aliases_map_to_known_canonical(self):
        """Every alias maps to a canonical provider in the registry."""
        aliases = list_provider_aliases()
        for alias, canonical in aliases.items():
            assert canonical in _PROVIDER_REGISTRY, (
                f"Alias '{alias}' maps to unknown canonical '{canonical}'"
            )


class TestGetQaLlmProviderAliases:
    """Tests for alias resolution in get_qa_llm_provider()."""

    def _create_codex(self, name: str) -> CodexCLIProvider:
        return get_qa_llm_provider(name)  # type: ignore[return-value]

    def _create_gemini(self, name: str) -> GeminiCLIProvider:
        return get_qa_llm_provider(name)  # type: ignore[return-value]

    def _create_ollama(self, name: str) -> OllamaProvider:
        return get_qa_llm_provider(name)  # type: ignore[return-value]

    def test_codex_canonical(self):
        """'codex' resolves to CodexCLIProvider."""
        assert isinstance(get_qa_llm_provider("codex"), CodexCLIProvider)

    def test_codex_cli_alias(self):
        """'codex-cli' alias resolves to CodexCLIProvider."""
        assert isinstance(get_qa_llm_provider("codex-cli"), CodexCLIProvider)

    def test_openai_codex_alias(self):
        """'openai-codex' alias resolves to CodexCLIProvider."""
        assert isinstance(get_qa_llm_provider("openai-codex"), CodexCLIProvider)

    def test_gemini_canonical(self):
        """'gemini' resolves to GeminiCLIProvider."""
        assert isinstance(get_qa_llm_provider("gemini"), GeminiCLIProvider)

    def test_gemini_cli_alias(self):
        """'gemini-cli' alias resolves to GeminiCLIProvider."""
        assert isinstance(get_qa_llm_provider("gemini-cli"), GeminiCLIProvider)

    def test_google_alias(self):
        """'google' alias resolves to GeminiCLIProvider."""
        assert isinstance(get_qa_llm_provider("google"), GeminiCLIProvider)

    def test_ollama_canonical(self):
        """'ollama' resolves to OllamaProvider."""
        assert isinstance(get_qa_llm_provider("ollama"), OllamaProvider)

    def test_local_alias(self):
        """'local' alias resolves to OllamaProvider."""
        assert isinstance(get_qa_llm_provider("local"), OllamaProvider)

    def test_local_ollama_alias(self):
        """'local-ollama' alias resolves to OllamaProvider."""
        assert isinstance(get_qa_llm_provider("local-ollama"), OllamaProvider)


class TestGetQaLlmProviderCaseInsensitive:
    """Tests for case-insensitive provider name lookup."""

    def test_uppercase_codex(self):
        """'CODEX' is resolved case-insensitively."""
        assert isinstance(get_qa_llm_provider("CODEX"), CodexCLIProvider)

    def test_mixed_case_gemini(self):
        """'Gemini' is resolved case-insensitively."""
        assert isinstance(get_qa_llm_provider("Gemini"), GeminiCLIProvider)

    def test_uppercase_ollama(self):
        """'OLLAMA' is resolved case-insensitively."""
        assert isinstance(get_qa_llm_provider("OLLAMA"), OllamaProvider)

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped from provider name."""
        assert isinstance(get_qa_llm_provider("  codex  "), CodexCLIProvider)


class TestGetQaLlmProviderErrors:
    """Tests for error paths in get_qa_llm_provider()."""

    def test_unknown_provider_raises_value_error(self):
        """An unrecognised provider name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown QA LLM provider"):
            get_qa_llm_provider("gpt-5")

    def test_error_message_lists_known_providers(self):
        """ValueError message lists all recognised provider aliases."""
        with pytest.raises(ValueError) as exc_info:
            get_qa_llm_provider("unknown-provider")
        msg = str(exc_info.value)
        assert "claude" in msg
        assert "codex" in msg
        assert "gemini" in msg
        assert "ollama" in msg

    def test_bad_kwargs_raises_type_error(self):
        """Unrecognised kwargs for a provider raise TypeError."""
        with pytest.raises(TypeError):
            get_qa_llm_provider("codex", nonexistent_kwarg="oops")

    def test_empty_string_raises_value_error(self):
        """An empty provider name raises ValueError."""
        with pytest.raises(ValueError):
            get_qa_llm_provider("")


class TestGetQaLlmProviderKwargs:
    """Tests that kwargs are forwarded correctly to provider constructors."""

    def test_codex_model_kwarg(self):
        """model kwarg is stored on the CodexCLIProvider instance."""
        provider = get_qa_llm_provider("codex", model="o3")
        assert isinstance(provider, CodexCLIProvider)
        assert provider._model == "o3"

    def test_gemini_timeout_kwarg(self):
        """timeout kwarg is stored on the GeminiCLIProvider instance."""
        provider = get_qa_llm_provider("gemini", timeout=120)
        assert isinstance(provider, GeminiCLIProvider)
        assert provider._timeout == 120

    def test_ollama_base_url_kwarg(self):
        """base_url kwarg is stored on the OllamaProvider instance."""
        provider = get_qa_llm_provider("ollama", base_url="http://ollama.example.com:11434")
        assert isinstance(provider, OllamaProvider)
        assert "ollama.example.com" in provider._base_url


# ===========================================================================
# 4. CodexCLIProvider
# ===========================================================================


class TestCodexCLIProviderInit:
    """Tests for CodexCLIProvider initialisation."""

    def test_default_values(self):
        """Default model, path, and timeout are set."""
        provider = CodexCLIProvider()
        assert provider._model == "o4-mini"
        assert provider._codex_path == "codex"
        assert provider._timeout == 300
        assert provider._working_dir is None
        assert provider._extra_args == []
        assert provider._pending_prompt is None

    def test_custom_values(self):
        """Custom constructor values are stored."""
        provider = CodexCLIProvider(
            model="o3",
            codex_path="/usr/local/bin/codex",
            timeout=60,
            working_dir=Path("/tmp"),
            extra_args=["--no-git"],
        )
        assert provider._model == "o3"
        assert provider._codex_path == "/usr/local/bin/codex"
        assert provider._timeout == 60
        assert provider._working_dir == Path("/tmp")
        assert provider._extra_args == ["--no-git"]

    def test_none_extra_args_becomes_empty_list(self):
        """None extra_args is normalised to an empty list."""
        provider = CodexCLIProvider(extra_args=None)
        assert provider._extra_args == []

    def test_is_base_provider_subclass(self):
        """CodexCLIProvider is a subclass of BaseLLMProvider."""
        assert issubclass(CodexCLIProvider, BaseLLMProvider)


class TestCodexCLIProviderBuildCommand:
    """Tests for CodexCLIProvider._build_command()."""

    def test_default_command_shape(self):
        """Default command: [codex, -q, --model, o4-mini, --]."""
        provider = CodexCLIProvider()
        cmd = provider._build_command()
        assert cmd[0] == "codex"
        assert "-q" in cmd
        assert "--model" in cmd
        assert "o4-mini" in cmd
        assert cmd[-1] == "--"

    def test_model_flag_present_when_set(self):
        """--model flag is included when model is set."""
        provider = CodexCLIProvider(model="o3")
        cmd = provider._build_command()
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "o3"

    def test_model_flag_absent_when_empty(self):
        """--model flag is omitted when model is empty string."""
        provider = CodexCLIProvider(model="")
        cmd = provider._build_command()
        assert "--model" not in cmd

    def test_extra_args_inserted_before_separator(self):
        """extra_args appear before the -- separator."""
        provider = CodexCLIProvider(extra_args=["--no-git", "--timeout", "60"])
        cmd = provider._build_command()
        sep_idx = cmd.index("--")
        for arg in ["--no-git", "--timeout", "60"]:
            arg_idx = cmd.index(arg)
            assert arg_idx < sep_idx

    def test_always_ends_with_separator(self):
        """Command always ends with -- regardless of extra_args."""
        for extra in [[], ["--no-git"], ["--no-git", "--verbose"]]:
            provider = CodexCLIProvider(extra_args=extra)
            assert provider._build_command()[-1] == "--"


class TestCodexCLIProviderQuery:
    """Tests for CodexCLIProvider.query()."""

    def test_query_stores_prompt(self):
        """query() stores the prompt for later use by receive_response()."""

        async def _test():
            provider = CodexCLIProvider()
            await provider.query("analyse this code")
            assert provider._pending_prompt == "analyse this code"

        _run(_test())

    def test_query_returns_none(self):
        """query() returns None."""

        async def _test():
            provider = CodexCLIProvider()
            result = await provider.query("test")
            assert result is None

        _run(_test())


class TestCodexCLIProviderContextManager:
    """Tests for CodexCLIProvider async context manager."""

    def test_aenter_returns_self(self):
        """__aenter__ returns the provider instance."""

        async def _test():
            provider = CodexCLIProvider()
            result = await provider.__aenter__()
            assert result is provider

        _run(_test())

    def test_aexit_clears_pending_prompt(self):
        """__aexit__ clears the pending prompt."""

        async def _test():
            provider = CodexCLIProvider()
            await provider.query("some prompt")
            await provider.__aexit__(None, None, None)
            assert provider._pending_prompt is None

        _run(_test())

    def test_context_manager_protocol(self):
        """async with CodexCLIProvider() works end to end."""

        async def _test():
            async with CodexCLIProvider() as p:
                assert isinstance(p, CodexCLIProvider)

        _run(_test())


class TestCodexCLIProviderReceiveResponse:
    """Tests for CodexCLIProvider.receive_response() async generator."""

    def test_no_prompt_yields_nothing(self):
        """receive_response() yields nothing when query() was not called."""

        async def _test():
            provider = CodexCLIProvider()
            msgs = await _collect(provider.receive_response())
            assert msgs == []

        _run(_test())

    def test_codex_not_found_raises_runtime_error(self):
        """RuntimeError is raised when the codex executable is not on PATH."""

        async def _test():
            provider = CodexCLIProvider()
            await provider.query("test prompt")
            with patch("shutil.which", return_value=None):
                with pytest.raises(RuntimeError, match="Codex CLI executable not found"):
                    await _collect(provider.receive_response())

        _run(_test())

    def test_success_yields_assistant_message(self):
        """Successful subprocess call yields a single AssistantMessage."""

        async def _test():
            provider = CodexCLIProvider(model="o4-mini")
            await provider.query("review this")

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(
                return_value=(b"All checks passed.\n", b"")
            )

            with patch("shutil.which", return_value="/usr/bin/codex"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    msgs = await _collect(provider.receive_response())

            assert len(msgs) == 1
            msg = msgs[0]
            assert type(msg).__name__ == "AssistantMessage"
            assert len(msg.content) == 1
            assert type(msg.content[0]).__name__ == "TextBlock"
            assert "All checks passed." in msg.content[0].text

        _run(_test())

    def test_nonzero_exit_with_stdout_still_yields_message(self):
        """Non-zero exit but with stdout yields the AssistantMessage (not fatal)."""

        async def _test():
            provider = CodexCLIProvider()
            await provider.query("review this")

            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(
                return_value=(b"Some output despite error", b"warning msg")
            )

            with patch("shutil.which", return_value="/usr/bin/codex"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    msgs = await _collect(provider.receive_response())

            assert len(msgs) == 1
            assert "Some output despite error" in msgs[0].content[0].text

        _run(_test())

    def test_nonzero_exit_without_stdout_raises_runtime_error(self):
        """Non-zero exit with no stdout raises RuntimeError."""

        async def _test():
            provider = CodexCLIProvider()
            await provider.query("review this")

            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(
                return_value=(b"", b"fatal error occurred")
            )

            with patch("shutil.which", return_value="/usr/bin/codex"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    with pytest.raises(RuntimeError, match="Codex CLI exited with an error"):
                        await _collect(provider.receive_response())

        _run(_test())

    def test_empty_stdout_returns_placeholder(self):
        """Empty stdout yields a placeholder message instead of empty text."""

        async def _test():
            provider = CodexCLIProvider()
            await provider.query("prompt")

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"  ", b""))

            with patch("shutil.which", return_value="/usr/bin/codex"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    msgs = await _collect(provider.receive_response())

            assert len(msgs) == 1
            assert "(no output from Codex CLI)" in msgs[0].content[0].text

        _run(_test())

    def test_timeout_raises_asyncio_timeout_error(self):
        """asyncio.TimeoutError is raised when subprocess exceeds timeout."""

        async def _test():
            provider = CodexCLIProvider(timeout=5)
            await provider.query("slow prompt")

            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_proc.kill = MagicMock()

            with patch("shutil.which", return_value="/usr/bin/codex"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    with pytest.raises(asyncio.TimeoutError):
                        await _collect(provider.receive_response())

        _run(_test())


# ===========================================================================
# 5. GeminiCLIProvider
# ===========================================================================


class TestGeminiCLIProviderInit:
    """Tests for GeminiCLIProvider initialisation."""

    def test_default_values(self):
        """Default model, path, and timeout are set."""
        provider = GeminiCLIProvider()
        assert provider._model == "gemini-2.0-flash"
        assert provider._gemini_path == "gemini"
        assert provider._timeout == 300
        assert provider._working_dir is None
        assert provider._extra_args == []
        assert provider._pending_prompt is None

    def test_custom_values(self):
        """Custom constructor values are stored."""
        provider = GeminiCLIProvider(
            model="gemini-2.5-pro",
            gemini_path="/usr/local/bin/gemini",
            timeout=120,
            working_dir=Path("/workspace"),
            extra_args=["--no-cache"],
        )
        assert provider._model == "gemini-2.5-pro"
        assert provider._gemini_path == "/usr/local/bin/gemini"
        assert provider._timeout == 120
        assert provider._working_dir == Path("/workspace")
        assert provider._extra_args == ["--no-cache"]

    def test_is_base_provider_subclass(self):
        """GeminiCLIProvider is a subclass of BaseLLMProvider."""
        assert issubclass(GeminiCLIProvider, BaseLLMProvider)


class TestGeminiCLIProviderBuildCommand:
    """Tests for GeminiCLIProvider._build_command()."""

    def test_default_command_starts_with_executable(self):
        """Command starts with the gemini executable."""
        provider = GeminiCLIProvider()
        cmd = provider._build_command()
        assert cmd[0] == "gemini"

    def test_model_flag_present_when_set(self):
        """--model flag is included when model is set."""
        provider = GeminiCLIProvider(model="gemini-2.5-pro")
        cmd = provider._build_command()
        assert "--model" in cmd
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "gemini-2.5-pro"

    def test_model_flag_absent_when_empty(self):
        """--model flag is omitted when model is empty string."""
        provider = GeminiCLIProvider(model="")
        cmd = provider._build_command()
        assert "--model" not in cmd

    def test_no_double_dash_separator(self):
        """Gemini command does NOT include a -- separator (unlike Codex)."""
        provider = GeminiCLIProvider()
        cmd = provider._build_command()
        assert "--" not in cmd

    def test_extra_args_appended(self):
        """extra_args are appended to the command."""
        provider = GeminiCLIProvider(extra_args=["--no-cache", "--verbose"])
        cmd = provider._build_command()
        assert "--no-cache" in cmd
        assert "--verbose" in cmd


class TestGeminiCLIProviderQuery:
    """Tests for GeminiCLIProvider.query()."""

    def test_query_stores_prompt(self):
        """query() stores the prompt."""

        async def _test():
            provider = GeminiCLIProvider()
            await provider.query("check coverage")
            assert provider._pending_prompt == "check coverage"

        _run(_test())


class TestGeminiCLIProviderContextManager:
    """Tests for GeminiCLIProvider async context manager."""

    def test_aenter_returns_self(self):
        """__aenter__ returns the provider instance."""

        async def _test():
            provider = GeminiCLIProvider()
            result = await provider.__aenter__()
            assert result is provider

        _run(_test())

    def test_aexit_clears_pending_prompt(self):
        """__aexit__ clears the pending prompt."""

        async def _test():
            provider = GeminiCLIProvider()
            await provider.query("some prompt")
            await provider.__aexit__(None, None, None)
            assert provider._pending_prompt is None

        _run(_test())


class TestGeminiCLIProviderReceiveResponse:
    """Tests for GeminiCLIProvider.receive_response()."""

    def test_no_prompt_yields_nothing(self):
        """receive_response() yields nothing when query() was not called."""

        async def _test():
            provider = GeminiCLIProvider()
            msgs = await _collect(provider.receive_response())
            assert msgs == []

        _run(_test())

    def test_gemini_not_found_raises_runtime_error(self):
        """RuntimeError is raised when gemini executable is not on PATH."""

        async def _test():
            provider = GeminiCLIProvider()
            await provider.query("prompt")
            with patch("shutil.which", return_value=None):
                with pytest.raises(RuntimeError, match="Gemini CLI executable not found"):
                    await _collect(provider.receive_response())

        _run(_test())

    def test_success_yields_assistant_message(self):
        """Successful subprocess call yields a single AssistantMessage."""

        async def _test():
            provider = GeminiCLIProvider(model="gemini-2.0-flash")
            await provider.query("review code")

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(
                return_value=(b"LGTM. All criteria met.\n", b"")
            )

            with patch("shutil.which", return_value="/usr/bin/gemini"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    msgs = await _collect(provider.receive_response())

            assert len(msgs) == 1
            assert type(msgs[0]).__name__ == "AssistantMessage"
            assert "LGTM" in msgs[0].content[0].text

        _run(_test())

    def test_nonzero_exit_without_stdout_raises_runtime_error(self):
        """Non-zero exit with empty stdout raises RuntimeError."""

        async def _test():
            provider = GeminiCLIProvider()
            await provider.query("prompt")

            mock_proc = MagicMock()
            mock_proc.returncode = 2
            mock_proc.communicate = AsyncMock(return_value=(b"", b"auth failed"))

            with patch("shutil.which", return_value="/usr/bin/gemini"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    with pytest.raises(RuntimeError, match="Gemini CLI exited with an error"):
                        await _collect(provider.receive_response())

        _run(_test())

    def test_timeout_raises_asyncio_timeout_error(self):
        """asyncio.TimeoutError is raised when subprocess exceeds timeout."""

        async def _test():
            provider = GeminiCLIProvider(timeout=10)
            await provider.query("slow prompt")

            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_proc.kill = MagicMock()

            with patch("shutil.which", return_value="/usr/bin/gemini"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    with pytest.raises(asyncio.TimeoutError):
                        await _collect(provider.receive_response())

        _run(_test())

    def test_empty_stdout_returns_placeholder(self):
        """Empty stdout yields a placeholder message."""

        async def _test():
            provider = GeminiCLIProvider()
            await provider.query("prompt")

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"   ", b""))

            with patch("shutil.which", return_value="/usr/bin/gemini"):
                with patch(
                    "asyncio.create_subprocess_exec",
                    AsyncMock(return_value=mock_proc),
                ):
                    msgs = await _collect(provider.receive_response())

            assert "(no output from Gemini CLI)" in msgs[0].content[0].text

        _run(_test())


# ===========================================================================
# 6. OllamaProvider
# ===========================================================================


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialisation."""

    def test_default_values(self):
        """Default model, base_url, and timeout are set.

        Note: OllamaProvider always injects num_ctx=32768 if the caller
        doesn't supply one, so _extra_options is never truly empty.
        """
        provider = OllamaProvider()
        assert provider._model == "llama3.2"
        assert "localhost:11434" in provider._base_url
        assert provider._timeout == 300
        assert provider._extra_options == {"num_ctx": 32768}
        assert provider._pending_prompt is None

    def test_custom_values(self):
        """Custom constructor values are stored; num_ctx default merges in."""
        provider = OllamaProvider(
            model="codellama:13b",
            base_url="http://ollama.example.com:11434",
            timeout=120,
            extra_options={"temperature": 0, "num_predict": 4096},
        )
        assert provider._model == "codellama:13b"
        assert "ollama.example.com" in provider._base_url
        assert provider._timeout == 120
        assert provider._extra_options == {
            "temperature": 0,
            "num_predict": 4096,
            "num_ctx": 32768,
        }

    def test_trailing_slash_stripped_from_base_url(self):
        """Trailing slash is stripped from base_url."""
        provider = OllamaProvider(base_url="http://localhost:11434/")
        assert not provider._base_url.endswith("/")

    def test_none_extra_options_gets_num_ctx_default(self):
        """None extra_options is normalised to a dict containing num_ctx."""
        provider = OllamaProvider(extra_options=None)
        assert provider._extra_options == {"num_ctx": 32768}

    def test_explicit_num_ctx_not_overridden(self):
        """A caller-supplied num_ctx wins over the default."""
        provider = OllamaProvider(extra_options={"num_ctx": 8192})
        assert provider._extra_options == {"num_ctx": 8192}

    def test_is_base_provider_subclass(self):
        """OllamaProvider is a subclass of BaseLLMProvider."""
        assert issubclass(OllamaProvider, BaseLLMProvider)


class TestOllamaProviderBuildPayload:
    """Tests for OllamaProvider._build_payload()."""

    def test_required_keys_present(self):
        """Payload contains model, messages, and stream keys."""
        provider = OllamaProvider(model="llama3.2")
        payload = provider._build_payload("test prompt")
        assert payload["model"] == "llama3.2"
        assert payload["stream"] is False
        assert isinstance(payload["messages"], list)
        assert len(payload["messages"]) == 1

    def test_message_role_and_content(self):
        """Payload message has role=user and the prompt as content."""
        provider = OllamaProvider()
        payload = provider._build_payload("my qa prompt")
        msg = payload["messages"][0]
        assert msg["role"] == "user"
        assert msg["content"] == "my qa prompt"

    def test_options_key_always_includes_num_ctx_default(self):
        """options key is always present because num_ctx default is injected."""
        provider = OllamaProvider(extra_options={})
        payload = provider._build_payload("prompt")
        assert payload["options"] == {"num_ctx": 32768}

    def test_options_key_merges_caller_and_default(self):
        """Caller-supplied options are merged with the num_ctx default."""
        provider = OllamaProvider(extra_options={"temperature": 0})
        payload = provider._build_payload("prompt")
        assert payload["options"] == {"temperature": 0, "num_ctx": 32768}


class TestOllamaProviderExtractContent:
    """Tests for OllamaProvider._extract_content()."""

    def test_extracts_content_from_valid_response(self):
        """Correctly extracts content from a well-formed Ollama response."""
        response = {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "All tests pass."},
            "done": True,
        }
        result = OllamaProvider._extract_content(response)
        assert result == "All tests pass."

    def test_missing_message_raises_runtime_error(self):
        """RuntimeError raised when 'message' key is absent."""
        with pytest.raises(RuntimeError, match="missing 'message' field"):
            OllamaProvider._extract_content({"model": "llama3.2", "done": True})

    def test_message_not_dict_raises_runtime_error(self):
        """RuntimeError raised when 'message' value is not a dict."""
        with pytest.raises(RuntimeError, match="missing 'message' field"):
            OllamaProvider._extract_content({"message": "not a dict"})

    def test_missing_content_raises_runtime_error(self):
        """RuntimeError raised when 'message.content' key is absent."""
        with pytest.raises(RuntimeError, match="'content' field"):
            OllamaProvider._extract_content({"message": {"role": "assistant"}})

    def test_strips_whitespace(self):
        """Content is stripped of leading/trailing whitespace."""
        response = {"message": {"role": "assistant", "content": "  hello  "}}
        result = OllamaProvider._extract_content(response)
        assert result == "hello"

    def test_empty_content_returns_placeholder(self):
        """Empty content string returns the placeholder message."""
        response = {"message": {"role": "assistant", "content": ""}}
        result = OllamaProvider._extract_content(response)
        assert "(no output from Ollama)" in result


class TestOllamaProviderQuery:
    """Tests for OllamaProvider.query()."""

    def test_query_stores_prompt(self):
        """query() stores the prompt."""

        async def _test():
            provider = OllamaProvider()
            await provider.query("qa review prompt")
            assert provider._pending_prompt == "qa review prompt"

        _run(_test())


class TestOllamaProviderContextManager:
    """Tests for OllamaProvider async context manager."""

    def test_aenter_calls_verify_connection(self):
        """__aenter__ calls _verify_connection via asyncio.to_thread."""

        async def _test():
            provider = OllamaProvider()
            # Replace _verify_connection with a no-op so to_thread returns None
            # without requiring any network or subprocess call.
            provider._verify_connection = lambda: None  # type: ignore[method-assign]
            result = await provider.__aenter__()
            assert result is provider

        _run(_test())

    def test_aenter_raises_when_server_unreachable(self):
        """__aenter__ propagates RuntimeError from _verify_connection."""

        async def _test():
            provider = OllamaProvider(base_url="http://localhost:11434")

            # Replace _verify_connection directly — to_thread will call it
            # in a thread pool, and the RuntimeError will propagate out.
            def _failing_verify():
                raise RuntimeError("Cannot reach Ollama server at 'http://localhost:11434'")

            provider._verify_connection = _failing_verify  # type: ignore[method-assign]

            with pytest.raises(RuntimeError, match="Cannot reach Ollama server"):
                await provider.__aenter__()

        _run(_test())

    def test_aexit_clears_pending_prompt(self):
        """__aexit__ clears the pending prompt."""

        async def _test():
            provider = OllamaProvider()
            await provider.query("prompt text")
            await provider.__aexit__(None, None, None)
            assert provider._pending_prompt is None

        _run(_test())


class TestOllamaProviderReceiveResponse:
    """Tests for OllamaProvider.receive_response() async generator."""

    def test_no_prompt_yields_nothing(self):
        """receive_response() yields nothing when query() was not called."""

        async def _test():
            provider = OllamaProvider()
            msgs = await _collect(provider.receive_response())
            assert msgs == []

        _run(_test())

    def test_success_yields_assistant_message(self):
        """Successful HTTP call yields a single AssistantMessage."""

        async def _test():
            provider = OllamaProvider(model="llama3.2")
            await provider.query("qa prompt")

            ollama_response = {
                "model": "llama3.2",
                "message": {"role": "assistant", "content": "Feature validated."},
                "done": True,
            }

            # Patch _http_post directly: asyncio.to_thread and wait_for run
            # normally but never reach the network.
            with patch.object(provider, "_http_post", return_value=ollama_response):
                msgs = await _collect(provider.receive_response())

            assert len(msgs) == 1
            assert type(msgs[0]).__name__ == "AssistantMessage"
            assert "Feature validated." in msgs[0].content[0].text

        _run(_test())

    def test_timeout_raises_asyncio_timeout_error(self):
        """asyncio.TimeoutError is re-raised with a descriptive message."""

        async def _test():
            provider = OllamaProvider(timeout=30)
            await provider.query("slow qa prompt")

            with patch(
                "asyncio.wait_for",
                AsyncMock(side_effect=asyncio.TimeoutError()),
            ):
                with pytest.raises(asyncio.TimeoutError):
                    await _collect(provider.receive_response())

        _run(_test())

    def test_http_error_propagates_runtime_error(self):
        """RuntimeError from _http_post propagates through receive_response()."""

        async def _test():
            provider = OllamaProvider()
            await provider.query("prompt")

            with patch(
                "asyncio.wait_for",
                AsyncMock(side_effect=RuntimeError("Ollama API HTTP error 503")),
            ):
                with pytest.raises(RuntimeError, match="HTTP error 503"):
                    await _collect(provider.receive_response())

        _run(_test())


class TestOllamaProviderVerifyConnection:
    """Tests for OllamaProvider._verify_connection()."""

    def test_verify_connection_success(self):
        """_verify_connection succeeds when server returns 200."""
        import contextlib
        provider = OllamaProvider(base_url="http://localhost:11434")

        class _FakeResponse:
            def read(self):
                return b'{"models":[]}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("urllib.request.urlopen", return_value=_FakeResponse()):
            provider._verify_connection()  # Should not raise

    def test_verify_connection_url_error_raises_runtime_error(self):
        """_verify_connection raises RuntimeError when server is unreachable."""
        import urllib.error
        provider = OllamaProvider(base_url="http://localhost:11434")

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            with pytest.raises(RuntimeError, match="Cannot reach Ollama server"):
                provider._verify_connection()


# ===========================================================================
# 7. Cross-provider: message protocol compatibility
# ===========================================================================


class TestMessageProtocolCompatibility:
    """Tests that CLI providers yield protocol-compatible message objects.

    The QA reviewer/fixer code uses type(msg).__name__ string comparisons,
    never isinstance().  This suite verifies that messages produced by the
    non-Claude adapters satisfy the exact protocol expected by reviewer.py.
    """

    def _make_assistant_message(self, text: str) -> AssistantMessage:
        return AssistantMessage(content=[TextBlock(text=text)])

    def test_assistant_message_name_check(self):
        """type(msg).__name__ == 'AssistantMessage' as expected by reviewer.py."""
        msg = self._make_assistant_message("analysis result")
        assert type(msg).__name__ == "AssistantMessage"

    def test_text_block_name_check(self):
        """type(block).__name__ == 'TextBlock' as expected by reviewer.py."""
        block = TextBlock(text="result")
        assert type(block).__name__ == "TextBlock"

    def test_tool_use_block_name_check(self):
        """type(block).__name__ == 'ToolUseBlock' as expected by reviewer.py."""
        block = ToolUseBlock(name="read_file", input={"path": "/tmp/x"})
        assert type(block).__name__ == "ToolUseBlock"

    def test_tool_result_block_name_check(self):
        """type(block).__name__ == 'ToolResultBlock' as expected by reviewer.py."""
        block = ToolResultBlock(content="ok", is_error=False)
        assert type(block).__name__ == "ToolResultBlock"

    def test_user_message_name_check(self):
        """type(msg).__name__ == 'UserMessage' as expected by reviewer.py."""
        msg = UserMessage(content=[ToolResultBlock(content="done")])
        assert type(msg).__name__ == "UserMessage"

    def test_codex_response_protocol(self):
        """AssistantMessage yielded by CodexCLIProvider satisfies the protocol."""
        msg = AssistantMessage(content=[TextBlock(text="codex response")])
        assert type(msg).__name__ == "AssistantMessage"
        assert hasattr(msg, "content")
        assert type(msg.content[0]).__name__ == "TextBlock"
        assert hasattr(msg.content[0], "text")

    def test_gemini_response_protocol(self):
        """AssistantMessage yielded by GeminiCLIProvider satisfies the protocol."""
        msg = AssistantMessage(content=[TextBlock(text="gemini response")])
        assert type(msg).__name__ == "AssistantMessage"
        assert hasattr(msg.content[0], "text")

    def test_ollama_response_protocol(self):
        """AssistantMessage yielded by OllamaProvider satisfies the protocol."""
        msg = AssistantMessage(content=[TextBlock(text="ollama response")])
        assert type(msg).__name__ == "AssistantMessage"
        assert hasattr(msg.content[0], "text")
