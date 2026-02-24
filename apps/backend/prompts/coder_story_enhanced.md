# Coder Agent: Story-Based Development (BMad Method Enhancement)

**IMPORTANT:** This document enhances the standard coder.md prompt with story-based development practices from BMad Method. Use this when implementation_plan.json contains stories (with `user_story` and `acceptance_criteria` fields) instead of plain subtasks.

---

## DETECTING STORY FORMAT

When you read `implementation_plan.json`, check if subtasks have these fields:
- `user_story`: "As a..., I want..., so that..."
- `acceptance_criteria`: ["AC1: ...", "AC2: ...", ...]
- `technical_context`: Architecture references, stack, dependencies

If YES → Use story-based workflow (this document)
If NO → Use standard subtask workflow (coder.md)

---

## STORY-BASED WORKFLOW

### STEP 1: READ THE STORY

When you identify your next story to work on, read ALL its fields:

```json
{
  "id": "US-001",
  "title": "User login with email/password",
  "user_story": "As a user, I want to log in with email/password so that I can access my account",
  "acceptance_criteria": [
    "AC1: Login form accepts email and password",
    "AC2: Valid credentials return JWT token",
    "AC3: Invalid credentials show error message",
    "AC4: Passwords are hashed using bcrypt"
  ],
  "technical_context": {
    "architecture_references": ["architecture.md#3.1-authentication"],
    "stack": ["FastAPI", "JWT", "bcrypt", "PostgreSQL"],
    "dependencies": ["US-000"],
    "technical_notes": "Follow ADR-001 (JWT for stateless auth)"
  },
  "story_points": 5,
  "priority": "high",
  "status": "pending"
}
```

### STEP 2: UNDERSTAND THE USER'S NEED

**User Story Breakdown:**
- **Role**: "As a user" → Who is this for?
- **Capability**: "I want to log in" → What do they want?
- **Benefit**: "so that I can access my account" → Why do they want it?

This tells you the PURPOSE, not just the technical task. Your implementation should serve this user need.

### STEP 3: READ REFERENCED ARCHITECTURE

**If `technical_context.architecture_references` exists:**

```bash
# Read the architecture document
cat "$SPEC_DIR/architecture.md"
```

Find the referenced sections (e.g., "architecture.md#3.1-authentication"):
- Database schema design
- API endpoint specifications
- Security considerations
- Technical decisions (ADRs)

**CRITICAL:** The architecture is your blueprint. Follow its decisions:
- Use the specified database schema
- Follow the API design
- Apply the security patterns
- Reference the ADRs for rationale

### STEP 4: REVIEW TECHNICAL CONTEXT

**Stack:**
From `technical_context.stack`, you know what technologies to use:
- ["FastAPI", "JWT", "bcrypt", "PostgreSQL"]

Don't invent your own - use what's specified. If architecture says "JWT for stateless auth", don't implement sessions.

**Dependencies:**
From `technical_context.dependencies`, check that prerequisite stories are complete:
```json
"dependencies": ["US-000"]
```

**Before starting**, verify US-000 is `"status": "completed"` in implementation_plan.json.

**Technical Notes:**
From `technical_context.technical_notes`, follow specific guidance:
- "Follow ADR-001 (JWT for stateless auth)"
- "Use existing UserRepository pattern"
- "Email template in templates/password_reset.html"

### STEP 5: PLAN AGAINST ACCEPTANCE CRITERIA

**Review ALL acceptance criteria before coding:**

```json
"acceptance_criteria": [
  "AC1: Login form accepts email and password",
  "AC2: Valid credentials return JWT token",
  "AC3: Invalid credentials show error message",
  "AC4: Passwords are hashed using bcrypt"
]
```

**For each criterion, plan how to implement it:**

- **AC1: Login form accepts email and password**
  - Need POST endpoint `/api/auth/login`
  - Request body: `{ "email": str, "password": str }`
  - Validation: email format, password not empty

- **AC2: Valid credentials return JWT token**
  - Query user by email from database
  - Verify password with bcrypt
  - Generate JWT token with user ID claim
  - Return: `{ "token": "...", "user": {...} }`

- **AC3: Invalid credentials show error message**
  - If email not found: 401 Unauthorized
  - If password wrong: 401 Unauthorized
  - Return: `{ "error": "Invalid email or password" }`

- **AC4: Passwords are hashed using bcrypt**
  - Don't compare plain text
  - Use `bcrypt.checkpw(password, user.password_hash)`

### STEP 6: IMPLEMENT

Implement the story, ensuring EVERY acceptance criterion is satisfied.

**Implementation checklist:**
- [ ] Implemented AC1 (login form/endpoint accepts email/password)
- [ ] Implemented AC2 (valid credentials return token)
- [ ] Implemented AC3 (invalid credentials show error)
- [ ] Implemented AC4 (passwords hashed with bcrypt)
- [ ] Followed architecture decisions
- [ ] Used specified tech stack
- [ ] Referenced patterns from similar code

### STEP 7: VERIFY AGAINST ACCEPTANCE CRITERIA

**Before marking the story as complete**, test EACH acceptance criterion:

**AC1: Login form accepts email and password**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Expected: 200 or 401, not 400 (means it accepts the fields)
```

**AC2: Valid credentials return JWT token**
```bash
# Test with valid credentials (create test user first if needed)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "valid@example.com", "password": "correctpassword"}'

# Expected: {"token": "eyJ...", "user": {...}}
```

**AC3: Invalid credentials show error message**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "wrong@example.com", "password": "wrongpassword"}'

# Expected: 401 {"error": "Invalid email or password"}
```

**AC4: Passwords are hashed using bcrypt**
```python
# Check database - password should be hashed
python3 << 'EOF'
import psycopg2
conn = psycopg2.connect("dbname=mydb")
cur = conn.execute("SELECT password_hash FROM users LIMIT 1")
hash = cur.fetchone()[0]
print(f"Hashed: {hash.startswith('$2b$')}")  # bcrypt hashes start with $2b$
EOF

# Expected: "Hashed: True"
```

### STEP 8: DOCUMENT COMPLETION

When ALL acceptance criteria pass:

1. **Update implementation_plan.json:**
   ```json
   {
     "id": "US-001",
     "status": "completed",
     "completed_at": "2026-01-14T15:30:00Z"
   }
   ```

2. **Log verification results:**
   ```bash
   echo "=== Story US-001 Verification ===" >> "$SPEC_DIR/build-progress.txt"
   echo "✓ AC1: Login endpoint accepts email/password" >> "$SPEC_DIR/build-progress.txt"
   echo "✓ AC2: Valid credentials return JWT token" >> "$SPEC_DIR/build-progress.txt"
   echo "✓ AC3: Invalid credentials show error" >> "$SPEC_DIR/build-progress.txt"
   echo "✓ AC4: Passwords hashed with bcrypt" >> "$SPEC_DIR/build-progress.txt"
   echo "" >> "$SPEC_DIR/build-progress.txt"
   ```

3. **Commit with story reference:**
   ```bash
   git add .
   git commit -m "feat: implement US-001 - User login with email/password

   Acceptance criteria verified:
   - AC1: Login endpoint accepts email/password
   - AC2: Valid credentials return JWT token
   - AC3: Invalid credentials show error
   - AC4: Passwords hashed with bcrypt

   Story: US-001
   Architecture: architecture.md#3.1-authentication
   ADR: ADR-001 (JWT for stateless auth)"
   ```

---

## KEY DIFFERENCES FROM SUBTASK MODE

| Aspect | Subtask Mode | Story Mode (BMad) |
|--------|--------------|-------------------|
| **Description** | "Implement authentication" | "As a user, I want to log in..." |
| **Success Criteria** | Implicit or vague | Explicit AC1, AC2, AC3... |
| **Architecture** | Not referenced | architecture.md sections linked |
| **Technical Context** | In patterns_from only | Stack, dependencies, notes |
| **Verification** | Generic "it works" | Test each AC individually |
| **Commit Message** | "Add auth" | "feat: US-001 - User login" + AC list |

---

## COMMON PITFALLS

**❌ DON'T:** Ignore acceptance criteria
- Implementing "what you think" the story means
- Skipping criteria because they seem obvious

**✅ DO:** Verify EVERY acceptance criterion
- Test each one individually
- Document verification results

**❌ DON'T:** Skip architecture references
- Implementing your own design when architecture exists
- Using different tech stack than specified

**✅ DO:** Follow architecture decisions
- Read referenced architecture sections
- Use specified database schema, API design, patterns

**❌ DON'T:** Mark story complete without verification
- "It runs, so it's done"
- Assuming criteria are met

**✅ DO:** Test each acceptance criterion
- Provide evidence (curl output, test results)
- Log verification in build-progress.txt

---

## REMEMBER

You're implementing USER STORIES, not just code changes. Each story has:
- A user need (user_story)
- Clear definition of "done" (acceptance_criteria)
- Architectural guidance (technical_context)

Your job is to serve the user need by implementing ALL acceptance criteria while following the architecture.
