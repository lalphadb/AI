# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2026-01-01 00:14]
S101 (assert statements) will flag 130 issues in tests - this is acceptable for test files and should be ignored via per-file-ignores in pyproject.toml

_Context: Ruff security scan of backend - S101 is expected in test files_

## [2026-01-01 00:20]
onnxruntime==1.19.2 is not available for Python 3.13 - only 1.20.0+ exists. pip-audit will fail if trying to resolve this. Use filtered requirements file excluding onnxruntime for auditing.

_Context: Running pip-audit on requirements.txt with Python 3.13 audit environment_
