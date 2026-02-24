# Contributing to Claude Code Manager Web

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Contributor License Agreement](#contributor-license-agreement)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Git Workflow](#git-workflow)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

---

## Contributor License Agreement

All contributors must agree to our simplified [CLA](CLA.md) before contributions can be accepted.

**How to sign:** Include in your PR description:
```
I have read the CLA and I agree to its terms.
```

Or use DCO sign-off on commits:
```bash
git commit -s -m "Your commit message"
```

---

## Prerequisites

Before contributing, ensure you have:

- **Node.js 24+** - For the frontend
- **Python 3.12+** - For the backend
- **npm 10+** - Package manager
- **Git** - Version control

### Installing Prerequisites

**Node.js:**
```bash
# macOS
brew install node@24

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs

# Windows
winget install OpenJS.NodeJS.LTS
```

**Python 3.12:**
```bash
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv

# Windows
winget install Python.Python.3.12
```

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/dataseeek/Claude-Code-Manager-Web.git
cd Claude-Code-Manager-Web

# Install all dependencies
npm run install:all

# Run in development mode
# Terminal 1: Backend
cd apps/web-server && source .venv/bin/activate && python -m server.main

# Terminal 2: Frontend
cd apps/frontend-web && npm run dev
```

---

## Development Setup

### Backend (Python)

```bash
cd apps/backend

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r ../../tests/requirements-test.txt

# Configure environment
cp .env.example .env
# Add your CLAUDE_CODE_OAUTH_TOKEN
```

### Web Server (FastAPI)

```bash
cd apps/web-server

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### Frontend (React)

```bash
cd apps/frontend-web

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## Code Style

### Python

- Follow **PEP 8** style guidelines
- Use **type hints** for function signatures
- Use **docstrings** for public functions
- Keep functions under 50 lines

```python
# Good
def get_next_subtask(spec_dir: Path) -> dict | None:
    """
    Find the next pending subtask in the implementation plan.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        The next subtask dict or None if complete
    """
    ...

# Avoid
def gns(sd):
    ...
```

### TypeScript/React

- Use **TypeScript strict mode**
- Use **functional components** with hooks
- Prefer **named exports**
- Use UI components from `src/components/ui/`

```typescript
// Good
export function TaskCard({ task, onEdit }: TaskCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  // ...
}

// Avoid
export default function(props) {
  // ...
}
```

### General

- No trailing whitespace
- End files with a newline
- 2 spaces for TypeScript/JSON, 4 spaces for Python
- Keep lines under 100 characters

---

## Testing

### Python Tests

```bash
cd apps/backend
source .venv/bin/activate

# Run all tests
.venv/bin/pytest ../../tests/ -v

# Run specific test file
.venv/bin/pytest ../../tests/test_security.py -v

# Skip slow tests
.venv/bin/pytest ../../tests/ -m "not slow"

# With coverage
.venv/bin/pytest ../../tests/ --cov=apps/backend
```

### Frontend Tests

```bash
cd apps/frontend-web

# Run tests
npm test

# Watch mode
npm run test:watch

# Type checking
npm run typecheck

# Linting
npm run lint
```

### Before Submitting

1. All existing tests must pass
2. New features should include tests
3. Bug fixes should include regression tests

---

## Git Workflow

### Branch Structure

```
develop                    ← Integration branch (PRs target here)
  │
  ├── feature/xxx          ← New features
  ├── fix/xxx              ← Bug fixes
  └── docs/xxx             ← Documentation
```

### Branch Naming

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New feature | `feature/add-dark-mode` |
| `fix/` | Bug fix | `fix/terminal-resize` |
| `docs/` | Documentation | `docs/update-readme` |
| `refactor/` | Code refactoring | `refactor/simplify-auth` |
| `test/` | Test additions | `test/add-api-tests` |
| `chore/` | Maintenance | `chore/update-deps` |

### Creating a Branch

```bash
# Always branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format
<type>: <description>

# Examples
feat: add terminal resize support
fix: resolve memory leak in WebSocket handler
docs: update API documentation
refactor: simplify authentication flow
test: add unit tests for task store
chore: update dependencies
```

---

## Pull Request Process

### 1. Create Your Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature
```

### 2. Make Changes

- Follow code style guidelines
- Write/update tests
- Update documentation if needed

### 3. Test Locally

```bash
# Python tests
npm run test:backend

# Frontend tests
cd apps/frontend-web
npm test
npm run typecheck
npm run lint
```

### 4. Commit and Push

```bash
git add .
git commit -s -m "feat: your feature description"
git push origin feature/your-feature
```

### 5. Create Pull Request

- Target the `develop` branch
- Use a clear, descriptive title
- Reference related issues
- Include CLA agreement
- Add screenshots for UI changes

### PR Title Format

```
<type>: <description>

Examples:
feat: Add WebSocket reconnection logic
fix: Resolve terminal resize issue on Firefox
docs: Update installation instructions
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing
How did you test these changes?

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] I agree to the CLA
```

---

## Issue Reporting

### Bug Reports

Include:

1. **Clear title** describing the issue
2. **Environment details** (OS, Node.js, Python versions)
3. **Steps to reproduce**
4. **Expected vs actual behavior**
5. **Error messages/logs**
6. **Screenshots** (for UI issues)

### Feature Requests

Include:

1. **Problem description** you're trying to solve
2. **Proposed solution**
3. **Alternatives considered**
4. **Use case context**

---

## Project Architecture

### Overview

```
Claude-Code-Manager-Web/
├── apps/
│   ├── frontend-web/     # React web frontend
│   ├── web-server/       # FastAPI backend
│   └── backend/          # Python agent system
├── tests/                # Test suite
├── scripts/              # Build scripts
└── guides/               # Documentation
```

For detailed architecture, see [DOCS.md](DOCS.md).

---

## Questions?

- **Issues:** https://github.com/dataseeek/Claude-Code-Manager-Web/issues
- **Discussions:** https://github.com/dataseeek/Claude-Code-Manager-Web/discussions

Thank you for contributing to Claude Code Manager Web!
