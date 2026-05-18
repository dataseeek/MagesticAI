"""
QA Reviewer Agent Session
==========================

Runs QA validation sessions to review implementation against
acceptance criteria.

Memory Integration:
- Retrieves past patterns, gotchas, and insights before QA session
- Saves QA findings (bugs, patterns, validation outcomes) after session
"""

from pathlib import Path

# Memory integration for cross-session learning
from agents.memory_manager import get_graphiti_context, save_session_memory
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from prompts_pkg import get_qa_reviewer_prompt
from providers.factory import get_tool_fallback_provider
from qa.providers import BaseLLMProvider
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)

from .criteria import get_qa_signoff_status

# =============================================================================
# QA REVIEWER SESSION
# =============================================================================


async def run_qa_agent_session(
    client: BaseLLMProvider,
    project_dir: Path,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    verbose: bool = False,
    previous_error: dict | None = None,
) -> tuple[str, str]:
    """
    Run a QA reviewer agent session.

    Args:
        client: LLM provider (BaseLLMProvider implementation)
        project_dir: Project root directory (for capability detection)
        spec_dir: Spec directory
        qa_session: QA iteration number
        max_iterations: Maximum number of QA iterations
        verbose: Whether to show detailed output
        previous_error: Error context from previous iteration for self-correction

    Returns:
        (status, response_text) where status is:
        - "approved" if QA approves
        - "rejected" if QA finds issues
        - "error" if an error occurred
    """
    debug_section("qa_reviewer", f"QA Reviewer Session {qa_session}")
    debug(
        "qa_reviewer",
        "Starting QA reviewer session",
        spec_dir=str(spec_dir),
        qa_session=qa_session,
        max_iterations=max_iterations,
    )

    print(f"\n{'=' * 70}")
    print(f"  QA REVIEWER SESSION {qa_session}")
    print("  Validating all acceptance criteria...")
    print(f"{'=' * 70}\n")

    # Get task logger for streaming markers
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0

    # Load QA prompt with dynamically-injected project-specific MCP tools
    # This includes Electron validation for Electron apps, Puppeteer for web, etc.
    prompt = get_qa_reviewer_prompt(spec_dir, project_dir)
    debug_detailed(
        "qa_reviewer",
        "Loaded QA reviewer prompt with project-specific tools",
        prompt_length=len(prompt),
        project_dir=str(project_dir),
    )

    # Retrieve memory context for QA (past patterns, gotchas, validation insights)
    qa_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "QA validation and acceptance criteria review",
            "id": f"qa_reviewer_{qa_session}",
        },
    )
    if qa_memory_context:
        prompt += "\n\n" + qa_memory_context
        print("✓ Memory context loaded for QA reviewer")
        debug_success("qa_reviewer", "Graphiti memory context loaded for QA")

    # Add session context
    prompt += f"\n\n---\n\n**QA Session**: {qa_session}\n"
    prompt += f"**Max Iterations**: {max_iterations}\n"

    # Add error context for self-correction if previous iteration failed
    if previous_error:
        debug(
            "qa_reviewer",
            "Adding error context for self-correction",
            error_type=previous_error.get("error_type"),
            consecutive_errors=previous_error.get("consecutive_errors"),
        )
        prompt += f"""

---

## ⚠️ CRITICAL: PREVIOUS ITERATION FAILED - SELF-CORRECTION REQUIRED

The previous QA session failed with the following error:

**Error**: {previous_error.get("error_message", "Unknown error")}
**Consecutive Failures**: {previous_error.get("consecutive_errors", 1)}

### What Went Wrong

You did NOT update the `implementation_plan.json` file with the required `qa_signoff` object.

### Required Action

After completing your QA review, you MUST:

1. **Read the current implementation_plan.json**:
   ```bash
   cat {spec_dir}/implementation_plan.json
   ```

2. **Update it with your qa_signoff** by editing the JSON file to add/update the `qa_signoff` field:

   If APPROVED:
   ```json
   {{
     "qa_signoff": {{
       "status": "approved",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "report_file": "qa_report.md",
       "tests_passed": {{"unit": "X/Y", "integration": "X/Y", "e2e": "X/Y"}},
       "verified_by": "qa_agent"
     }}
   }}
   ```

   If REJECTED:
   ```json
   {{
     "qa_signoff": {{
       "status": "rejected",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "issues_found": [
         {{"type": "critical", "title": "[issue]", "location": "[file:line]", "fix_required": "[description]"}}
       ],
       "fix_request_file": "QA_FIX_REQUEST.md"
     }}
   }}
   ```

3. **Use the Edit tool or Write tool** to update the file. The file path is:
   `{spec_dir}/implementation_plan.json`

### FAILURE TO DO THIS WILL CAUSE ANOTHER ERROR

This is attempt {previous_error.get("consecutive_errors", 1) + 1}. If you fail to update implementation_plan.json again, the QA process will be escalated to human review.

---

"""
        print(
            f"\n⚠️  Retry with self-correction context (attempt {previous_error.get('consecutive_errors', 1) + 1})"
        )

    try:
        debug("qa_reviewer", "Sending query to Claude SDK...")
        await client.query(prompt)
        debug_success("qa_reviewer", "Query sent successfully")

        response_text = ""
        debug("qa_reviewer", "Starting to receive response stream...")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            message_count += 1
            debug_detailed(
                "qa_reviewer",
                f"Received message #{message_count}",
                msg_type=msg_type,
            )

            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        response_text += block.text
                        print(block.text, end="", flush=True)
                        # Log text to task logger (persist without double-printing)
                        if task_logger and block.text.strip():
                            task_logger.log(
                                block.text,
                                LogEntryType.TEXT,
                                LogPhase.VALIDATION,
                                print_to_console=False,
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input_display = None
                        tool_count += 1

                        # Safely extract tool input (handles None, non-dict, etc.)
                        inp = get_safe_tool_input(block)

                        # Extract tool input for display
                        if inp:
                            if "file_path" in inp:
                                fp = inp["file_path"]
                                if len(fp) > 50:
                                    fp = "..." + fp[-47:]
                                tool_input_display = fp
                            elif "pattern" in inp:
                                tool_input_display = f"pattern: {inp['pattern']}"

                        debug(
                            "qa_reviewer",
                            f"Tool call #{tool_count}: {tool_name}",
                            tool_input=tool_input_display,
                        )

                        # Log tool start (handles printing)
                        if task_logger:
                            task_logger.tool_start(
                                tool_name,
                                tool_input_display,
                                LogPhase.VALIDATION,
                                print_to_console=True,
                            )
                        else:
                            print(f"\n[QA Tool: {tool_name}]", flush=True)

                        if verbose and hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 300:
                                print(f"   Input: {input_str[:300]}...", flush=True)
                            else:
                                print(f"   Input: {input_str}", flush=True)
                        current_tool = tool_name

            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "ToolResultBlock":
                        is_error = getattr(block, "is_error", False)
                        result_content = getattr(block, "content", "")

                        if is_error:
                            debug_error(
                                "qa_reviewer",
                                f"Tool error: {current_tool}",
                                error=str(result_content)[:200],
                            )
                            error_str = str(result_content)[:500]
                            print(f"   [Error] {error_str}", flush=True)
                            if task_logger and current_tool:
                                # Store full error in detail for expandable view
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result=error_str[:100],
                                    detail=str(result_content),
                                    phase=LogPhase.VALIDATION,
                                )
                        else:
                            debug_detailed(
                                "qa_reviewer",
                                f"Tool success: {current_tool}",
                                result_length=len(str(result_content)),
                            )
                            if verbose:
                                result_str = str(result_content)[:200]
                                print(f"   [Done] {result_str}", flush=True)
                            else:
                                print("   [Done]", flush=True)
                            if task_logger and current_tool:
                                # Store full result in detail for expandable view
                                detail_content = None
                                if current_tool in (
                                    "Read",
                                    "Grep",
                                    "Bash",
                                    "Edit",
                                    "Write",
                                ):
                                    result_str = str(result_content)
                                    if len(result_str) < 50000:
                                        detail_content = result_str
                                task_logger.tool_end(
                                    current_tool,
                                    success=True,
                                    detail=detail_content,
                                    phase=LogPhase.VALIDATION,
                                )

                        current_tool = None

        print("\n" + "-" * 70 + "\n")

        # Check the QA result from implementation_plan.json
        status = get_qa_signoff_status(spec_dir)
        debug(
            "qa_reviewer",
            "QA session completed",
            message_count=message_count,
            tool_count=tool_count,
            response_length=len(response_text),
            qa_status=status.get("status") if status else "unknown",
        )

        # Save QA session insights to memory
        qa_discoveries = {
            "files_understood": {},
            "patterns_found": [],
            "gotchas_encountered": [],
        }

        if status and status.get("status") == "approved":
            debug_success("qa_reviewer", "QA APPROVED")
            qa_discoveries["patterns_found"].append(
                f"QA session {qa_session}: All acceptance criteria validated successfully"
            )
            # Save successful QA session to memory
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=True,
                subtasks_completed=[f"qa_reviewer_{qa_session}"],
                discoveries=qa_discoveries,
            )
            return "approved", response_text
        elif status and status.get("status") == "rejected":
            debug_error("qa_reviewer", "QA REJECTED")
            # Extract issues found for memory
            issues = status.get("issues_found", [])
            for issue in issues:
                qa_discoveries["gotchas_encountered"].append(
                    f"QA Issue ({issue.get('type', 'unknown')}): {issue.get('title', 'No title')} at {issue.get('location', 'unknown')}"
                )
            # Save rejected QA session to memory (learning from failures)
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=False,
                subtasks_completed=[],
                discoveries=qa_discoveries,
            )
            return "rejected", response_text
        else:
            # Agent didn't update the status properly.
            # If we have text output but no tool calls, try a tool-capable
            # fallback provider (Claude → Codex → Gemini) to write the
            # qa_signoff based on the text analysis.
            if tool_count == 0 and response_text:
                debug(
                    "qa_reviewer",
                    "Text-only provider returned analysis without tools — "
                    "attempting tool-capable fallback",
                    response_length=len(response_text),
                )
                fallback_result = await _run_tool_fallback(
                    response_text, spec_dir, project_dir, qa_session, task_logger
                )
                if fallback_result is not None:
                    fb_status, fb_text = fallback_result
                    return fb_status, fb_text

            # No fallback available or fallback also failed
            debug_error(
                "qa_reviewer",
                "QA agent did not update implementation_plan.json",
                message_count=message_count,
                tool_count=tool_count,
                response_preview=response_text[:500] if response_text else "empty",
            )

            # Build informative error message for feedback loop
            error_details = []
            if message_count == 0:
                error_details.append("No messages received from agent")
            if tool_count == 0:
                error_details.append("No tools were used by agent")
            if not response_text:
                error_details.append("Agent produced no output")

            error_msg = "QA agent did not update implementation_plan.json"
            if error_details:
                error_msg += f" ({'; '.join(error_details)})"

            return "error", error_msg

    except Exception as e:
        debug_error(
            "qa_reviewer",
            f"QA session exception: {e}",
            exception_type=type(e).__name__,
        )
        print(f"Error during QA session: {e}")
        if task_logger:
            task_logger.log_error(f"QA session error: {e}", LogPhase.VALIDATION)
        return "error", str(e)


# =============================================================================
# TOOL-USE FALLBACK FOR TEXT-ONLY PROVIDERS
# =============================================================================


async def _run_tool_fallback(
    qa_analysis: str,
    spec_dir: Path,
    project_dir: Path,
    qa_session: int,
    task_logger,
) -> tuple[str, str] | None:
    """Use a tool-capable provider to write qa_signoff based on text analysis.

    When a text-only provider (Ollama) returns QA analysis text but cannot
    update implementation_plan.json (no tool use), this function delegates
    the file update to the first available tool-capable provider
    (Claude → Codex → Gemini).

    Args:
        qa_analysis: The QA analysis text from the text-only provider.
        spec_dir: Spec directory containing implementation_plan.json.
        project_dir: Project root directory.
        qa_session: Current QA iteration number.
        task_logger: Task logger for progress tracking.

    Returns:
        (status, response_text) if the fallback succeeded, or None if no
        fallback provider is available or the fallback also failed.
    """
    fallback = get_tool_fallback_provider(
        phase="qa",
        exclude="ollama",
        working_dir=project_dir,
    )
    if fallback is None:
        debug_error(
            "qa_reviewer",
            "No tool-capable fallback provider available",
        )
        return None

    provider_name = type(fallback).__name__
    print(f"\n🔄 Delegating file update to {provider_name}...")
    debug(
        "qa_reviewer",
        f"Tool fallback: using {provider_name} to write qa_signoff",
    )

    if task_logger:
        task_logger.log(
            f"Text-only provider completed analysis. Delegating file update to {provider_name}...",
            LogEntryType.INFO,
            LogPhase.VALIDATION,
        )

    # Build a focused prompt for the fallback: just update the JSON file
    fallback_prompt = f"""You are a QA file updater. A separate QA reviewer agent has already analyzed the code and produced the following analysis. Your ONLY job is to:

1. Read the analysis below
2. Determine if the QA result is APPROVED or REJECTED
3. Update the file `{spec_dir}/implementation_plan.json` with the appropriate `qa_signoff` object

## QA Analysis from Reviewer

{qa_analysis[:8000]}

## Instructions

Read `{spec_dir}/implementation_plan.json`, then update it by adding/updating the `qa_signoff` field:

If the analysis indicates ALL criteria pass (APPROVED):
```json
{{
  "qa_signoff": {{
    "status": "approved",
    "timestamp": "[current ISO timestamp]",
    "qa_session": {qa_session},
    "verified_by": "qa_agent"
  }}
}}
```

If the analysis indicates issues (REJECTED):
```json
{{
  "qa_signoff": {{
    "status": "rejected",
    "timestamp": "[current ISO timestamp]",
    "qa_session": {qa_session},
    "issues_found": [
      {{"type": "critical|major|minor", "title": "[issue]", "location": "[file:line]", "fix_required": "[description]"}}
    ]
  }}
}}
```

IMPORTANT: You MUST read and then write the implementation_plan.json file. Do NOT just output text.
"""

    try:
        async with fallback:
            await fallback.query(fallback_prompt)
            fb_response = ""
            fb_tool_count = 0
            async for msg in fallback.receive_response():
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            fb_response += block.text
                        elif block_type == "ToolUseBlock":
                            fb_tool_count += 1

        # Check if the fallback actually wrote qa_signoff
        status = get_qa_signoff_status(spec_dir)
        if status and status.get("status") in ("approved", "rejected"):
            result_status = status["status"]
            debug_success(
                "qa_reviewer",
                f"Tool fallback succeeded: QA {result_status}",
                fallback_provider=provider_name,
                tool_count=fb_tool_count,
            )
            print(f"✅ {provider_name} successfully wrote qa_signoff: {result_status}")
            if task_logger:
                task_logger.log(
                    f"Tool fallback ({provider_name}) wrote qa_signoff: {result_status}",
                    LogEntryType.SUCCESS,
                    LogPhase.VALIDATION,
                )
            return result_status, qa_analysis

        debug_error(
            "qa_reviewer",
            f"Tool fallback ({provider_name}) did not write qa_signoff",
            tool_count=fb_tool_count,
        )
        return None

    except Exception as exc:
        debug_error(
            "qa_reviewer",
            f"Tool fallback ({provider_name}) failed: {exc}",
        )
        print(f"⚠️  Fallback {provider_name} failed: {exc}")
        return None
