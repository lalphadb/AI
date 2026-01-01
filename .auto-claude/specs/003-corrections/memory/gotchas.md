# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2026-01-01 00:14]
S101 (assert statements) will flag 130 issues in tests - this is acceptable for test files and should be ignored via per-file-ignores in pyproject.toml

_Context: Ruff security scan of backend - S101 is expected in test files_
