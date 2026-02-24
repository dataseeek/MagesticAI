# Claude Code Manager Web - Troubleshooting Guide

This guide helps you diagnose and resolve common issues with Claude Code Manager Web. It covers installation problems, authentication errors, connection issues, and performance troubleshooting.

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Authentication Problems](#authentication-problems)
4. [Connection & Network Issues](#connection--network-issues)
5. [Terminal Issues](#terminal-issues)
6. [Task Execution Issues](#task-execution-issues)
7. [Memory System (Graphiti) Issues](#memory-system-graphiti-issues)
8. [Git & Worktree Issues](#git--worktree-issues)
9. [UI & Browser Issues](#ui--browser-issues)
10. [Performance Issues](#performance-issues)
11. [Debug Mode](#debug-mode)
12. [Log File Locations](#log-file-locations)
13. [FAQ](#faq)
14. [Getting Help](#getting-help)

---

## Quick Diagnostics

Run these commands to quickly diagnose common issues:

```bash
# Check Node.js version (requires 24+)
node --version

# Check Python version (requires 3.12+)
python3 --version

# Check if web server is running
curl http://localhost:8000/health

# Check backend authentication
cd apps/backend && source .venv/bin/activate && python -c "import os; print('Token set:', bool(os.getenv('CLAUDE_CODE_OAUTH_TOKEN')))"

# Check web server token
cat ~/.auto-claude-web/.token 2>/dev/null || echo "No token file found"

# Check if ports are in use
lsof -i :8000  # Web server
lsof -i :5173  # Frontend dev server
```

### Health Check Endpoints

| Endpoint | Expected Response |
|----------|------------------|
| `GET /health` | `{"status": "healthy"}` |
| `GET /api/settings` | Settings JSON (requires auth) |

---

## Installation Issues

### Node.js Version Too Old

**Symptom:** `npm install` fails with syntax errors or unsupported features.

**Solution:**
```bash
# Check current version
node --version  # Should be v24.x or higher

# Install Node.js 24+
# macOS
brew install node@24

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows
winget install OpenJS.NodeJS.LTS
```

### Python Version Incompatible

**Symptom:** `pip install` fails with dependency errors or syntax errors.

**Solution:**
```bash
# Check current version
python3 --version  # Should be 3.12+

# Install Python 3.12
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv python3.12-dev

# Windows
winget install Python.Python.3.12
```

### Dependencies Not Found

**Symptom:** `ModuleNotFoundError` or `Cannot find module` errors.

**Solution:**
```bash
# Reinstall all dependencies from project root
npm run install:all

# Or reinstall individually:
# Frontend
cd apps/frontend-web && npm install

# Web server
cd apps/web-server && pip install -r requirements.txt

# Backend
cd apps/backend && pip install -r requirements.txt
```

### Virtual Environment Issues

**Symptom:** Python packages not found despite being installed.

**Solution:**
```bash
# Ensure you're in the correct virtual environment
cd apps/backend

# Check if venv exists
ls -la .venv/

# Recreate virtual environment if corrupted
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Permission Denied Errors

**Symptom:** `EACCES` errors during npm install or file access errors.

**Solution:**
```bash
# Fix npm permissions (Linux/macOS)
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) /usr/local/lib/node_modules

# Fix project permissions
sudo chown -R $(whoami) .

# For token file
chmod 600 ~/.auto-claude-web/.token
```

---

## Authentication Problems

### "Invalid or expired token" Error

**Symptom:** API requests return 401 Unauthorized.

**Causes and Solutions:**

1. **Missing API token:**
   ```bash
   # Check if token exists
   cat ~/.auto-claude-web/.token

   # If missing, start the web server - it auto-generates a token
   cd apps/web-server && python -m server.main
   ```

2. **Token mismatch:**
   ```bash
   # Get the current token
   cat ~/.auto-claude-web/.token

   # Ensure browser is using the correct token
   # Check browser DevTools → Network → Request Headers → Authorization
   ```

3. **Corrupted token file:**
   ```bash
   # Regenerate token
   rm ~/.auto-claude-web/.token
   cd apps/web-server && python -m server.main
   ```

### Claude Code OAuth Token Issues

**Symptom:** "Authentication failed" when running AI tasks.

**Solution:**
```bash
# Get a fresh OAuth token
claude setup-token

# Add token to backend .env
echo "CLAUDE_CODE_OAUTH_TOKEN=your-new-token" >> apps/backend/.env

# Verify token is loaded
cd apps/backend
source .venv/bin/activate
python -c "import os; print(os.getenv('CLAUDE_CODE_OAUTH_TOKEN', 'NOT SET')[:20])"
```

### Token Expiration

**Symptom:** Tasks fail after working previously.

**Solution:**
```bash
# Refresh your Claude Code token
claude setup-token

# Update the token in apps/backend/.env
nano apps/backend/.env
# Replace CLAUDE_CODE_OAUTH_TOKEN value

# Restart the web server
pkill -f "server.main"
cd apps/web-server && python -m server.main
```

### Enterprise/CCR Authentication

**Symptom:** CCR proxy authentication fails.

**Solution:**
```bash
# Ensure CCR token format is correct
# In apps/backend/.env:
ANTHROPIC_AUTH_TOKEN=sk-zcf-x-ccr

# Set custom endpoint
ANTHROPIC_BASE_URL=http://127.0.0.1:3456

# Verify CCR is running
curl http://127.0.0.1:3456/health
```

---

## Connection & Network Issues

### "Connection Refused" Error

**Symptom:** Frontend can't connect to backend.

**Causes and Solutions:**

1. **Web server not running:**
   ```bash
   # Start the web server
   cd apps/web-server
   source .venv/bin/activate
   python -m server.main
   ```

2. **Wrong port:**
   ```bash
   # Check which port is configured
   grep APP_PORT apps/web-server/.env

   # Default is 8000, ensure frontend uses the same
   ```

3. **Firewall blocking:**
   ```bash
   # Allow port 8000 (Linux)
   sudo ufw allow 8000

   # Windows Firewall
   netsh advfirewall firewall add rule name="Claude Web" dir=in action=allow protocol=tcp localport=8000
   ```

### WebSocket Connection Failed

**Symptom:** Real-time updates not working, terminal freezes.

**Solution:**
```bash
# Check WebSocket connection in browser DevTools
# Network tab → WS filter → Check for ws://localhost:8000/ws/events

# Common fixes:
# 1. Disable browser extensions that block WebSockets
# 2. Check CORS settings in apps/web-server/.env:
APP_CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# 3. Try a different browser
# 4. Clear browser cache and cookies
```

### CORS Errors

**Symptom:** Browser console shows "Access-Control-Allow-Origin" errors.

**Solution:**
```bash
# Edit apps/web-server/.env
APP_CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"]

# Restart web server
pkill -f "server.main"
cd apps/web-server && python -m server.main
```

### Proxy/VPN Issues

**Symptom:** Connections timeout or fail intermittently.

**Solution:**
```bash
# Bypass proxy for localhost
# In apps/backend/.env:
NO_PROXY=127.0.0.1,localhost

# Or configure proxy:
HTTP_PROXY=http://your-proxy:8080
HTTPS_PROXY=http://your-proxy:8080
```

---

## Terminal Issues

### Terminal Not Opening

**Symptom:** Clicking "New Terminal" does nothing.

**Solution:**
```bash
# Check maximum terminals limit
grep APP_MAX_TERMINALS apps/web-server/.env
# Default is 20, increase if needed

# Check for shell availability
which bash  # or which zsh

# Set explicit shell path
# In apps/web-server/.env:
APP_DEFAULT_SHELL=/bin/bash
```

### Terminal Output Garbled

**Symptom:** Terminal shows incorrect characters or colors.

**Solution:**
1. **Set correct terminal type:**
   ```bash
   # In your shell profile (~/.bashrc or ~/.zshrc)
   export TERM=xterm-256color
   ```

2. **Adjust terminal font in settings:**
   - Go to Settings → Terminal
   - Try different font sizes (12-16 work best)

3. **Clear terminal state:**
   - Press `Ctrl+C` to interrupt
   - Type `reset` to reset terminal

### Terminal Disconnected

**Symptom:** Terminal shows "Disconnected" or stops responding.

**Solution:**
```bash
# Reconnect by refreshing the browser

# If persistent, kill orphaned PTY sessions:
pkill -f "python.*pty"

# Restart web server
pkill -f "server.main"
cd apps/web-server && python -m server.main
```

### Commands Not Executing

**Symptom:** Commands typed but nothing happens.

**Solution:**
```bash
# Check shell is properly configured
echo $SHELL

# Ensure .bashrc/.zshrc doesn't hang on non-interactive shells
# Add this at the top of your shell config:
[[ $- != *i* ]] && return

# Check if there's a hanging process
ps aux | grep -E "bash|zsh"
```

---

## Task Execution Issues

### Task Stuck in "Pending" Status

**Symptom:** Task never starts executing.

**Solution:**
```bash
# Check if backend is properly configured
cd apps/backend
source .venv/bin/activate
python -c "import os; print('OAuth Token:', 'SET' if os.getenv('CLAUDE_CODE_OAUTH_TOKEN') else 'MISSING')"

# Verify web server can reach backend
curl http://localhost:8000/api/settings

# Check for maximum concurrent task limits
grep APP_MAX_CONCURRENT_TASKS apps/web-server/.env
```

### Task Fails Immediately

**Symptom:** Task enters "Failed" status within seconds.

**Causes and Solutions:**

1. **Invalid OAuth token:**
   ```bash
   # Refresh token
   claude setup-token
   # Update apps/backend/.env
   ```

2. **Missing worktree:**
   ```bash
   # Check if worktree exists
   ls -la .auto-claude/worktrees/tasks/YOUR-TASK-ID/

   # If missing, the task may need to be recreated
   ```

3. **Invalid spec file:**
   ```bash
   # Check spec syntax
   cat .auto-claude/specs/YOUR-TASK-ID/spec.md

   # Ensure implementation_plan.json is valid JSON
   python -m json.tool .auto-claude/specs/YOUR-TASK-ID/implementation_plan.json
   ```

### QA Validation Loop

**Symptom:** Task keeps cycling between "QA Review" and "QA Fixing".

**Solution:**
1. **Manual intervention:**
   - Open the Task Detail Modal
   - Review the QA issues
   - Click "Human Review" to take control

2. **Skip QA:**
   ```bash
   # From CLI
   cd apps/backend
   python run.py --spec YOUR-TASK-ID --skip-qa
   ```

3. **Adjust acceptance criteria:**
   - Edit `.auto-claude/specs/YOUR-TASK-ID/spec.md`
   - Clarify or relax acceptance criteria

### Agent Process Crashed

**Symptom:** Task stuck mid-execution, logs stop updating.

**Solution:**
```bash
# Check for running agent processes
ps aux | grep -E "planner|coder|qa_reviewer"

# Kill stuck processes
pkill -f "python.*agents"

# Restart the task from the UI or CLI
cd apps/backend
python run.py --spec YOUR-TASK-ID
```

---

## Memory System (Graphiti) Issues

### "Graphiti connection failed"

**Symptom:** Memory features don't work, context not persisting.

**Solution:**
```bash
# Check if Graphiti is enabled
grep GRAPHITI_ENABLED apps/backend/.env
# Should be: GRAPHITI_ENABLED=true

# Check database path
ls -la ~/.auto-claude/memories/

# Verify LLM provider credentials
grep OPENAI_API_KEY apps/backend/.env  # or your configured provider
```

### Embedding Model Errors

**Symptom:** "Embedding dimension mismatch" or similar errors.

**Solution:**
```bash
# Ensure embedding dimensions match your model
# In apps/backend/.env for Ollama:
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768

# Clear and rebuild memory database
rm -rf ~/.auto-claude/memories/
# Restart the application
```

### Memory Not Being Stored

**Symptom:** Context lost between sessions.

**Solution:**
```bash
# Check if memory service is running
# Look in web server logs for Graphiti initialization

# Verify write permissions
touch ~/.auto-claude/memories/test.txt && rm ~/.auto-claude/memories/test.txt

# Check for errors in debug log
grep -i graphiti ~/.auto-claude-web/debug.log 2>/dev/null
```

### Offline Mode Not Working

**Symptom:** Graphiti fails without internet when using Ollama.

**Solution:**
```bash
# Ensure Ollama is running
ollama serve

# Verify Ollama is accessible
curl http://localhost:11434/api/version

# Pull required models
ollama pull deepseek-r1:7b
ollama pull nomic-embed-text

# Configure for offline
# In apps/backend/.env:
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Git & Worktree Issues

### "Worktree already exists"

**Symptom:** Task creation fails with worktree error.

**Solution:**
```bash
# List existing worktrees
git worktree list

# Remove orphaned worktree
git worktree remove .auto-claude/worktrees/tasks/TASK-ID --force

# Prune worktree references
git worktree prune
```

### "Cannot create worktree: branch already exists"

**Symptom:** Branch name collision.

**Solution:**
```bash
# Delete the conflicting branch
git branch -D task/TASK-ID

# Remove the worktree if it exists
git worktree remove .auto-claude/worktrees/tasks/TASK-ID --force

# Retry task creation
```

### Merge Conflicts

**Symptom:** Task cannot be merged automatically.

**Solution:**
1. **From the UI:**
   - Navigate to the Worktrees view
   - Click on the conflicted task
   - Use the "Open in Terminal" option
   - Resolve conflicts manually

2. **From CLI:**
   ```bash
   cd .auto-claude/worktrees/tasks/TASK-ID/
   git status  # See conflicted files
   # Edit files to resolve conflicts
   git add .
   git commit -m "Resolve merge conflicts"
   ```

### Detached HEAD State

**Symptom:** Git commands fail in worktree.

**Solution:**
```bash
cd .auto-claude/worktrees/tasks/TASK-ID/

# Check current state
git status

# Checkout the task branch
git checkout -b task/TASK-ID
```

### Worktree Directory Missing

**Symptom:** Task shows but worktree folder doesn't exist.

**Solution:**
```bash
# Prune invalid worktrees
git worktree prune

# Recreate the worktree
git worktree add .auto-claude/worktrees/tasks/TASK-ID -b task/TASK-ID main
```

---

## UI & Browser Issues

### White Screen / App Won't Load

**Symptom:** Browser shows blank page.

**Solution:**
```bash
# Check browser console for errors (F12 → Console)

# Common fixes:
# 1. Clear browser cache
# 2. Disable browser extensions
# 3. Try incognito/private mode
# 4. Check if frontend is running:
lsof -i :5173

# Rebuild frontend if corrupted
cd apps/frontend-web
rm -rf node_modules dist
npm install
npm run dev
```

### Components Not Rendering

**Symptom:** Parts of the UI are missing or broken.

**Solution:**
```bash
# Clear Vite cache
cd apps/frontend-web
rm -rf node_modules/.vite
npm run dev

# Check for TypeScript errors
npm run typecheck
```

### Keyboard Shortcuts Not Working

**Symptom:** Shortcuts like `Ctrl+K` don't respond.

**Solution:**
1. **Check focus:** Click inside the application window
2. **Disable conflicting extensions:** Browser extensions may capture shortcuts
3. **Check modal state:** Some shortcuts only work when no modal is open
4. **Browser shortcuts:** Some browsers reserve certain key combinations

### Dark/Light Mode Not Switching

**Symptom:** Theme toggle doesn't change appearance.

**Solution:**
1. **Force theme in settings:**
   - Settings → Appearance → Theme
   - Select "Dark" or "Light" instead of "System"

2. **Clear cached settings:**
   ```bash
   rm ~/.auto-claude-web/settings.json
   # Restart the application
   ```

### Slow UI Response

**Symptom:** UI feels laggy or unresponsive.

**Solution:**
1. **Reduce open terminals:** Close unused terminal sessions
2. **Clear browser data:** Cache, localStorage
3. **Check memory usage:** Browser task manager
4. **Reduce UI scale:** Settings → Appearance → UI Scale

---

## Performance Issues

### High CPU Usage

**Symptom:** System becomes slow during task execution.

**Solution:**
```bash
# Reduce concurrent tasks
# In apps/web-server/.env:
APP_MAX_CONCURRENT_TASKS=2

# Reduce terminal count
APP_MAX_TERMINALS=10

# Use lighter model for simple tasks
# In apps/backend/.env:
AUTO_BUILD_MODEL=claude-sonnet-4-5-20250929
```

### High Memory Usage

**Symptom:** Application or system runs out of memory.

**Solution:**
```bash
# Limit terminal buffer size
# Close unused terminals from the UI

# Prune git objects
git gc --aggressive

# Clear Vite cache
cd apps/frontend-web
rm -rf node_modules/.vite

# Restart the application periodically
```

### Slow Task Execution

**Symptom:** AI tasks take longer than expected.

**Solution:**
1. **Check network latency:**
   ```bash
   ping api.anthropic.com
   ```

2. **Use appropriate model:**
   - Simple tasks → Haiku or Sonnet
   - Complex tasks → Opus

3. **Reduce thinking level:**
   - Settings → Claude → Thinking Level → Standard

4. **Check API rate limits:**
   - Review Anthropic dashboard for rate limit status

### Slow File Operations

**Symptom:** Reading/writing files is slow.

**Solution:**
```bash
# Check disk space
df -h

# Check for large node_modules
du -sh apps/frontend-web/node_modules

# Clear build artifacts
rm -rf apps/frontend-web/dist
rm -rf apps/web-server/static

# Check for large log files
du -sh ~/.auto-claude-web/
```

---

## Debug Mode

### Enabling Debug Mode

Debug mode provides detailed logging for troubleshooting.

**Backend Debug:**
```bash
# In apps/backend/.env:
DEBUG=true
DEBUG_LEVEL=2  # 1=basic, 2=detailed, 3=verbose

# Optional: Log to file
DEBUG_LOG_FILE=debug.log
```

**Web Server Debug:**
```bash
# In apps/web-server/.env:
APP_DEBUG=true

# This enables:
# - Detailed error messages
# - API documentation at /docs
# - Request/response logging
```

### Debug Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `1` | Basic logging | General troubleshooting |
| `2` | Detailed logging | API and agent debugging |
| `3` | Verbose logging | Deep debugging, captures everything |

### Reading Debug Output

```bash
# Watch backend logs in real-time
tail -f apps/backend/debug.log

# Search for specific errors
grep -i error apps/backend/debug.log

# View web server output
# Logs appear in the terminal where server.main is running
```

### API Request Debugging

When `APP_DEBUG=true`:

1. Open `http://localhost:8000/docs` for Swagger UI
2. Test endpoints interactively
3. View request/response details

---

## Log File Locations

### Application Logs

| Log Type | Location | Content |
|----------|----------|---------|
| **Backend Debug** | `apps/backend/debug.log` (if configured) | Agent execution logs |
| **Web Server** | Terminal stdout | API requests, WebSocket events |
| **Task Logs** | `.auto-claude/specs/TASK-ID/logs/` | Per-task execution logs |
| **Graphiti** | `~/.auto-claude/memories/graphiti.log` | Memory system logs |

### Task-Specific Logs

```bash
# Find task logs
ls .auto-claude/specs/YOUR-TASK-ID/

# View implementation plan
cat .auto-claude/specs/YOUR-TASK-ID/implementation_plan.json

# Check build progress
cat .auto-claude/specs/YOUR-TASK-ID/build-progress.txt

# View context
cat .auto-claude/specs/YOUR-TASK-ID/context.json
```

### System Logs

```bash
# View recent system messages (Linux)
journalctl -u claude-code-manager --since "1 hour ago"

# macOS system log
log show --predicate 'processName == "python"' --last 1h

# Check for crash logs
ls /var/log/ | grep -i crash
```

### Clearing Logs

```bash
# Clear old task logs (keeps last 10)
find .auto-claude/specs -name "*.log" -mtime +7 -delete

# Clear backend debug log
> apps/backend/debug.log

# Clear memory logs
> ~/.auto-claude/memories/graphiti.log
```

---

## FAQ

### General

**Q: How do I completely reset the application?**

A: Remove configuration and data directories:
```bash
rm -rf ~/.auto-claude-web
rm -rf .auto-claude/worktrees
rm -rf .auto-claude/specs
# Then restart the application
```

**Q: How do I update to the latest version?**

A:
```bash
git pull origin main
npm run install:all
# Restart the application
```

**Q: Can I run multiple instances?**

A: Yes, but use different ports:
```bash
# Instance 1
APP_PORT=8000 python -m server.main

# Instance 2 (different terminal)
APP_PORT=8001 python -m server.main
```

### Authentication

**Q: Why does my token expire?**

A: Claude Code OAuth tokens expire periodically. Refresh with `claude setup-token`.

**Q: Can I use an API key instead of OAuth?**

A: No, direct API keys are not supported to prevent unexpected billing. Use OAuth tokens only.

**Q: How do I authenticate in a CI/CD environment?**

A: Use the `CLAUDE_CODE_OAUTH_TOKEN` environment variable in your CI/CD secrets.

### Tasks

**Q: Why did my task fail silently?**

A: Check the task logs in `.auto-claude/specs/TASK-ID/`. Enable debug mode for more details.

**Q: Can I retry a failed task?**

A: Yes, from the Kanban board, click on the task and use "Retry" or "Restart Phase".

**Q: How do I cancel a running task?**

A: Click the task card in Kanban and use the "Cancel" action. The worktree is preserved.

**Q: What happens to my code if a task fails?**

A: The worktree remains intact. You can review changes, fix issues manually, and merge.

### Performance

**Q: How much disk space does Claude Code Manager use?**

A: Typically 500MB-1GB per project, including worktrees and node_modules.

**Q: Can I run on a low-memory system?**

A: Yes, but limit concurrent tasks to 1-2 and close unused terminals.

**Q: Does it work offline?**

A: Partially. The UI works offline, but AI tasks require internet (unless using local Ollama for Graphiti).

### Integrations

**Q: How do I connect to a private GitHub repository?**

A: Ensure your `GITHUB_TOKEN` has `repo` scope, or authenticate with `gh auth login`.

**Q: Can I use GitLab self-hosted?**

A: Yes, set `GITLAB_INSTANCE_URL` to your GitLab URL.

**Q: Does it work with other AI providers?**

A: Currently only Anthropic Claude is supported for task execution. Graphiti supports multiple providers.

---

## Getting Help

### Before Asking for Help

1. **Check this guide** for your specific issue
2. **Enable debug mode** and review logs
3. **Update to the latest version**
4. **Search existing issues** on GitHub

### Information to Include

When reporting an issue, include:

```markdown
## Environment
- OS: [e.g., Ubuntu 24.04, macOS 15, Windows 11]
- Node.js version: [output of `node --version`]
- Python version: [output of `python3 --version`]
- Browser: [e.g., Chrome 130, Firefox 132]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [Error occurs]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Logs
[Paste relevant log output]

## Screenshots
[If applicable]
```

### Support Channels

| Channel | Best For |
|---------|----------|
| **[GitHub Issues](https://github.com/dataseeek/Claude-Code-Manager-Web/issues)** | Bug reports, feature requests |
| **[GitHub Discussions](https://github.com/dataseeek/Claude-Code-Manager-Web/discussions)** | Questions, help requests |
| **Documentation** | Self-help, learning |

### Useful Commands for Support

```bash
# Generate system information
echo "=== System Info ===" && \
node --version && \
python3 --version && \
git --version && \
echo "=== Disk Space ===" && \
df -h . && \
echo "=== Memory ===" && \
free -h 2>/dev/null || vm_stat
```

---

## Related Guides

- **[Getting Started](GETTING-STARTED.md)** - Initial setup guide
- **[Configuration](CONFIGURATION.md)** - All configuration options
- **[Development Setup](DEVELOPMENT-SETUP.md)** - Developer environment
- **[CLI Usage](CLI-USAGE.md)** - Command-line reference
- **[Architecture](ARCHITECTURE.md)** - System design details

---

**Still stuck?** Don't hesitate to [open an issue](https://github.com/dataseeek/Claude-Code-Manager-Web/issues/new) - we're here to help!
