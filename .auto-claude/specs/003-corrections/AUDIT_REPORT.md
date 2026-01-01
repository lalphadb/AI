# Security Audit Report: AI Orchestrator v5.2

**Audit Date:** 2026-01-01
**Auditor:** auto-claude
**Scope:** backend/ service - Security, Code Quality, Dependencies, Docker

---

## Executive Summary

| Severity | Count | Status |
|----------|-------|--------|
| **CRITICAL** | 3 | Pending Fix |
| **HIGH** | 8 | Pending Fix |
| **MEDIUM** | 15 | Documented (Out of Scope) |
| **LOW** | 50+ | Documented (Out of Scope) |

**Overall Risk Assessment:** HIGH - Critical security issues require immediate remediation.

**Tools Used:**
- Ruff 0.14.10 (Security, Code Quality)
- Pylint 4.0.4 (Code Quality)
- pip-audit 2.10.0 (Dependency Vulnerabilities)
- Vulture 2.14 (Dead Code Detection)

---

## CRITICAL Severity Issues

Issues that must be fixed immediately. They pose severe security risks.

### CRITICAL-001: SQL Injection Vulnerability
- **Tool:** Ruff S608
- **File:** `backend/auth.py:327`
- **Description:** SQL query constructed using f-string interpolation, allowing potential SQL injection attacks.
- **Risk:** An attacker could manipulate database queries, leading to data theft, modification, or deletion.
- **Remediation:** Use parameterized queries with `?` placeholders.
- **Status:** PENDING

### CRITICAL-002: Deprecated datetime.utcnow() Usage
- **Tool:** Manual Review / Pylint / Python 3.12 Deprecation Warning
- **File:** `ai-orchestrator/backend/auth.py`
- **Lines:** 350, 351, 359, 432 (4 occurrences total)
- **Description:** `datetime.utcnow()` is deprecated in Python 3.12+. Returns naive datetime objects which can cause timezone-related bugs in JWT token handling.
- **Risk:** Token expiration calculations may be incorrect, potentially extending token validity or causing authentication failures. Can also cause comparison issues with timezone-aware datetimes.
- **Python Deprecation Notice:** `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use datetime.datetime.now(datetime.timezone.utc) instead.`

#### Affected Code Locations

**Line 350 (create_access_token - token expiry):**
```python
# BEFORE (deprecated)
expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
```

**Line 351 (create_access_token - issued at time):**
```python
# BEFORE (deprecated)
to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})
```

**Line 359 (create_refresh_token - session expiry):**
```python
# BEFORE (deprecated)
expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
```

**Line 432 (create_api_key - API key expiry):**
```python
# BEFORE (deprecated)
expires_at = datetime.utcnow() + timedelta(days=expires_days)
```

#### Remediation Strategy

1. **Update imports** (Line 11):
   ```python
   # BEFORE
   from datetime import datetime, timedelta

   # AFTER
   from datetime import datetime, timedelta, timezone
   ```

2. **Replace all occurrences** with `datetime.now(timezone.utc)`:
   ```python
   # AFTER (all 4 locations)
   datetime.now(timezone.utc)
   ```

3. **Verification command:**
   ```bash
   grep -c 'utcnow' ai-orchestrator/backend/auth.py  # Should return 0 after fix
   grep -c 'timezone.utc' ai-orchestrator/backend/auth.py  # Should return >= 4 after fix
   ```

- **Status:** PENDING

### CRITICAL-003: Insecure Temporary File Creation
- **Tool:** Ruff S306
- **File:** `backend/` (location TBD)
- **Description:** Use of `tempfile.mktemp()` which creates a predictable file name, vulnerable to race conditions and symlink attacks.
- **Risk:** Attacker could predict temp file name and create malicious symlink, leading to file overwrites or data leakage.
- **Remediation:** Use `tempfile.mkstemp()` or `tempfile.NamedTemporaryFile()` instead.
- **Status:** PENDING

---

## HIGH Severity Issues

Issues that should be fixed as part of this audit cycle.

### HIGH-001: Deprecated python-jose Dependency (CVE-2024-33663, CVE-2024-33664)
- **Tool:** pip-audit
- **File:** `ai-orchestrator/backend/requirements.txt:36`
- **Package:** `python-jose[cryptography]==3.3.0`
- **Vulnerabilities:**
  - **PYSEC-2024-232 (CVE-2024-33663):** Algorithm confusion with OpenSSH ECDSA keys, allows signature bypass.
  - **PYSEC-2024-233 (CVE-2024-33664):** JWT bomb attack - crafted JWE token causes denial of service.
- **Risk:** Authentication bypass, denial of service.

#### Code Analysis

**Codebase Search Results:**
- `grep -r "from jose\|import jose" ai-orchestrator/backend/` → **0 matches**
- `python-jose` is listed in requirements.txt but is **NOT imported or used anywhere** in the codebase
- The project already uses `PyJWT==2.9.0` (line 27 in requirements.txt) for all JWT operations

**Conclusion:** `python-jose` is a legacy/unused dependency that can be safely removed without any code changes.

#### Removal Plan

1. **Delete the dependency line** from `ai-orchestrator/backend/requirements.txt`:
   ```diff
   - python-jose[cryptography]==3.3.0
   ```

2. **No code changes required** - the codebase already uses PyJWT exclusively:
   ```python
   # Current JWT usage in auth.py (uses jwt, not jose)
   import jwt  # PyJWT
   token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
   ```

3. **Verify no import errors** after removal:
   ```bash
   cd ai-orchestrator/backend && python3 -c "import auth; import main; print('OK')"
   ```

4. **Re-run pip-audit** to confirm vulnerability is resolved:
   ```bash
   pip-audit -r ai-orchestrator/backend/requirements.txt | grep -E 'python-jose|ecdsa'
   # Should return empty (both python-jose and its transitive ecdsa dependency removed)
   ```

#### Impact

Removing `python-jose` will also resolve:
- **HIGH-004 (ecdsa CVE-2024-23342):** Transitive dependency removed automatically

- **Status:** PENDING

### HIGH-002: Vulnerable python-multipart (CVE-2024-53981)
- **Tool:** pip-audit
- **File:** `backend/requirements.txt`
- **Package:** `python-multipart==0.0.12`
- **Description:** DoS vulnerability - malicious form data can cause excessive logging and CPU consumption.
- **Fix Version:** 0.0.18+
- **Status:** PENDING

### HIGH-003: Vulnerable Starlette (Transitive) - CVE-2024-47874, CVE-2025-54121
- **Tool:** pip-audit
- **File:** `backend/requirements.txt` (via FastAPI)
- **Package:** `starlette==0.38.6`
- **Vulnerabilities:**
  - **CVE-2024-47874:** Memory exhaustion via multipart form fields without filename.
  - **CVE-2025-54121:** Event loop blocking on large file uploads.
- **Fix Version:** 0.47.2+
- **Remediation:** Upgrade FastAPI to version that includes fixed Starlette, or pin starlette>=0.47.2.
- **Status:** PENDING

### HIGH-004: ecdsa Timing Attack (CVE-2024-23342)
- **Tool:** pip-audit
- **File:** `backend/requirements.txt` (transitive via python-jose)
- **Package:** `ecdsa==0.19.1`
- **Description:** Minerva timing attack on P-256 curve, may leak private key via timing analysis.
- **Fix:** No fix available. Package maintainers consider side-channel attacks out of scope.
- **Remediation:** Removing `python-jose` will remove this transitive dependency.
- **Status:** PENDING (resolved by removing python-jose)

### HIGH-005: Insecure Hash Function Usage
- **Tool:** Ruff S324
- **Files:** `backend/` (3 occurrences)
- **Description:** Use of MD5 or SHA1 which are cryptographically weak.
- **Risk:** Hash collisions may be exploitable for data integrity bypass.
- **Remediation:** Use SHA-256 or stronger. Verify if used for security purposes or just checksums.
- **Status:** PENDING (review required)

### HIGH-006: Pylint Score Below Target
- **Tool:** Pylint
- **Current Score:** 8.20/10
- **Target Score:** 9.0/10
- **Gap:** 0.80 points
- **Major Issues:**
  - 26+ logging f-string interpolations (W1203)
  - 15+ broad exception catches (W0718)
  - 19+ unused imports (W0611)
  - Module too large: main.py has 1425 lines (limit: 1000)
- **Status:** PENDING

### HIGH-007: Ruff Security Rules Not Configured
- **Tool:** Ruff config analysis
- **File:** `backend/pyproject.toml`
- **Description:** Security rules (S prefix) not in Ruff select list.
- **Remediation:** Add `"S"`, `"C4"`, `"UP"` to the Ruff select configuration.
- **Status:** PENDING

### HIGH-008: Hardcoded Password Detection
- **Tool:** Ruff S105, S106
- **Files:** `backend/` (10 occurrences combined)
- **Description:** Potential hardcoded passwords or credentials in source code.
- **Risk:** Credential exposure if code is leaked.
- **Remediation:** Review each occurrence. Move to environment variables if real credentials. Mark false positives with `# noqa: S105`.
- **Status:** PENDING (review required)

---

## MEDIUM Severity Issues

Documented but not fixed in this audit cycle per spec.

### MEDIUM-001: Dockerfile Runs as Root
- **File:** `backend/Dockerfile`
- **Description:** Container runs as root user, violating principle of least privilege.
- **Remediation:** Add non-root user: `RUN useradd -m appuser && USER appuser`

### MEDIUM-002: Docker Compose Missing Resource Limits
- **File:** `docker-compose.yml`
- **Description:** No memory or CPU limits configured for containers.
- **Remediation:** Add `deploy.resources.limits` with `memory: 2G` and `cpus: "2.0"`

### MEDIUM-003: Subprocess with Partial Path (S607)
- **Count:** 8 occurrences
- **Description:** Subprocess calls using commands without full path, vulnerable to PATH manipulation.

### MEDIUM-004: Bare Except Clauses (E722)
- **Count:** 4 occurrences
- **Files:** `main.py`
- **Description:** Catching all exceptions hides bugs and catches system-exit signals.

### MEDIUM-005: Missing Exception Chaining (B904)
- **Count:** 3 occurrences
- **Description:** `raise X` inside `except` block should use `raise X from exc`.

### MEDIUM-006: Module Too Large
- **File:** `main.py`
- **Lines:** 1425 (limit: 1000)
- **Description:** Module exceeds recommended size, reducing maintainability.

### MEDIUM-007: Exception Swallowed (S110)
- **Count:** 4 occurrences
- **Description:** Empty `except: pass` blocks hide errors silently.

### MEDIUM-008: Too Many Local Variables
- **File:** `main.py:1124`
- **Count:** 22 variables (limit: 15)

### MEDIUM-009: Too Many Branches
- **Files:** `main.py:1124`, `engine.py:142`
- **Count:** Up to 42 branches (limit: 12)

### MEDIUM-010: Too Many Statements
- **Files:** `main.py:1124`, `engine.py:142`
- **Count:** Up to 133 statements (limit: 50)

### MEDIUM-011: Import Outside Toplevel
- **Count:** 20+ occurrences
- **Description:** Imports inside functions reduce readability and can hide circular dependencies.

### MEDIUM-012: Unnecessary Pass Statements
- **File:** `security.py`
- **Lines:** 145, 151, 157

### MEDIUM-013: Missing Class/Function Docstrings
- **Count:** 15+ occurrences
- **Description:** Missing documentation for classes and functions.

### MEDIUM-014: Subprocess.run Without check=True
- **File:** `main.py`
- **Count:** 7 occurrences
- **Description:** Subprocess failures may be silently ignored.

### MEDIUM-015: Open Without Encoding
- **File:** `main.py`
- **Lines:** 1028, 1336
- **Description:** `open()` calls without explicit encoding may behave differently across platforms.

---

## LOW Severity Issues

Documented for reference. Can be fixed opportunistically.

### LOW-001: Binding to All Interfaces (S104)
- **Count:** 2 occurrences
- **Description:** Binding to `0.0.0.0` exposes service on all network interfaces.

### LOW-002: Hardcoded Temporary File Paths (S108)
- **Count:** 9 occurrences
- **Description:** Using hardcoded paths like `/tmp/` instead of platform-agnostic temp directories.

### LOW-003: try-except-continue (S112)
- **Count:** 1 occurrence
- **Description:** Exception handling that continues loop may hide errors.

### LOW-004: Line Too Long (E501)
- **Count:** 103 occurrences
- **Description:** Lines exceeding 100 characters reduce readability.

### LOW-005: Unused Imports (F401)
- **Count:** 56 occurrences
- **Description:** Imports that are never used should be removed.
- **Auto-fixable:** Yes, with `ruff check --fix`

### LOW-006: Unsorted Imports (I001)
- **Count:** 22 occurrences
- **Description:** Imports not following isort conventions.
- **Auto-fixable:** Yes, with `ruff check --fix`

### LOW-007: Python 3.12+ Modernization (UP006, UP045, UP035)
- **Count:** 228 occurrences combined
- **Description:**
  - UP006: Use `list` instead of `typing.List`
  - UP045: Use `X | None` instead of `Optional[X]`
  - UP035: Deprecated typing imports
- **Auto-fixable:** Yes, with `ruff check --fix`

### LOW-008: Redundant Open Modes (UP015)
- **Count:** 7 occurrences
- **Description:** `open(file, "r")` can be simplified to `open(file)`.

### LOW-009: Function Call in Default Argument (B008)
- **Count:** 14 occurrences
- **Description:** FastAPI `Depends()` pattern - acceptable in this context.

### LOW-010: Unused Loop Control Variable (B007)
- **Count:** 3 occurrences

### LOW-011: Zip Without Strict (B905)
- **Count:** 3 occurrences

### LOW-012: Assert Statements in Tests (S101)
- **Count:** 130 occurrences
- **Description:** Expected in test files. Configure per-file-ignores in pyproject.toml.

### LOW-013: f-string Missing Placeholders (F541)
- **Count:** 2 occurrences

### LOW-014: Ambiguous Variable Names (E741)
- **Count:** 2 occurrences

### LOW-015: True/False Comparison (E712)
- **Count:** 2 occurrences

---

## Dead Code Analysis (Vulture)

### Results
- **100% Confidence:** 0 issues found
- **90% Confidence:** 11 unused imports (overlaps with Ruff F401)
- **60% Confidence:** Multiple false positives identified

### Known False Positives
These are NOT dead code - they are used dynamically:
- FastAPI route handlers (endpoint functions)
- Pytest fixtures with `@pytest.fixture`
- Pydantic `model_config` class attributes
- Dynamically loaded tool functions in `tools/*.py`
- Watchdog event handlers

---

## Statistics Summary

### Ruff Findings
| Category | Count |
|----------|-------|
| Total Errors | 625 |
| Auto-fixable | 249 |
| Security (S*) | 170 |
| Code Quality (E*) | 112 |
| Unused Code (F*) | 60 |
| Import Order (I*) | 22 |
| Modernization (UP*) | 238 |
| Bugbear (B*) | 24 |

### Pylint Findings
| Metric | Value |
|--------|-------|
| Current Score | 8.20/10 |
| Target Score | 9.0/10 |
| Total Messages | 159 |
| Files Analyzed | 5 (core files) |

### Dependency Vulnerabilities
| Package | CVEs | Fix Available |
|---------|------|---------------|
| python-jose | 2 | Remove (deprecated) |
| python-multipart | 1 | Upgrade to 0.0.18 |
| starlette | 2 | Upgrade to 0.47.2 |
| ecdsa | 1 | No fix (remove python-jose) |

---

## Remediation Plan

### Phase 1: CRITICAL Fixes (Immediate)
1. Fix SQL injection in auth.py (CRITICAL-001)
2. Replace datetime.utcnow() with datetime.now(timezone.utc) (CRITICAL-002)
3. Replace mktemp with secure alternatives (CRITICAL-003)

### Phase 2: HIGH Fixes (This Sprint)
1. Remove python-jose dependency (HIGH-001, HIGH-004)
2. Upgrade python-multipart to 0.0.18+ (HIGH-002)
3. Upgrade/pin starlette to 0.47.2+ (HIGH-003)
4. Review hardcoded password detections (HIGH-005, HIGH-008)
5. Configure Ruff security rules (HIGH-007)
6. Fix Pylint issues to reach 9.0 score (HIGH-006)

### Phase 3: MEDIUM Fixes (Future Sprint)
1. Add non-root user to Dockerfile
2. Add resource limits to docker-compose.yml
3. Refactor main.py to reduce complexity
4. Fix exception handling patterns

### Phase 4: LOW Cleanup (Ongoing)
1. Run `ruff check --fix` for auto-fixable issues
2. Remove unused imports
3. Apply Python 3.12+ modernizations

---

## Appendix: Tool Commands

```bash
# Ruff security scan
ruff check --select=E,F,I,S,B,C4,UP backend/

# Pylint analysis
pylint --fail-under=9.0 backend/main.py backend/auth.py backend/security.py backend/config.py backend/engine.py

# Dependency audit
pip-audit -r backend/requirements.txt

# Dead code detection
vulture backend/ --min-confidence 100

# Auto-fix safe issues
ruff check --fix backend/
```

---

*Report generated by auto-claude security audit workflow*
