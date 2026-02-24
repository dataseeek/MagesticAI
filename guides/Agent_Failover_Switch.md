## Claude Account Failover Plan

Goal: When an agent run exits immediately with no logs (exit code 1, planning failed), automatically switch to another Claude account token from `~/.auto-claude-web/claude-profiles.json` and retry once.

### Strategy
- **Token resolution with failover order:**
  1) If `CLAUDE_CODE_OAUTH_TOKEN` is set in env, use it (no failover unless explicitly allowed).
  2) Else, read `~/.auto-claude-web/claude-profiles.json`:
     - Prefer active profile if it has `oauthToken` (or legacy `token`).
     - Else first usable profile; allow exclusion of the just-failed profile ID.
  3) Fallback: `~/.claude/oauth_token`.
- **Runtime failover in agent_service.py:**
  - On task start, set `CLAUDE_CODE_OAUTH_TOKEN` from chosen profile token (unless env override is present).
  - If subprocess exits with code != 0 and task log has no entries (early failure), retry once:
    - Exclude the failed profile ID, resolve next token, set env, and relaunch the same command.
    - Emit a WebSocket/log message noting profile switch and retry.
    - If no alternate token, surface failure as usual.
  - Detect rate-limit lines (e.g., "You've hit your limit", "rate limit", 429) in streamed output and allow the same single failover even if logs were already written.
- **Persist/trace:**
  - Optionally annotate `task_logs.json` or emitted events with which profile was used.
  - Avoid infinite retries (one fallback attempt only).
- **Testing:**
  - Add a test that mocks `claude-profiles.json` with two profiles; simulate first-run failure and assert the second profile token is used on retry, with only one retry.

### Notes
- Keep compatibility with env override behavior: if `CLAUDE_CODE_OAUTH_TOKEN` is explicitly set, do not auto-switch unless a dedicated flag is added.
- Auto-switch settings in `settings.py` can be respected later; don’t block this initial failover on them.
