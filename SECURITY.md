# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting a vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue
2. Send an email describing the vulnerability, steps to reproduce, and potential impact
3. Allow reasonable time for a fix before public disclosure

## Scope

kandidat is designed as a **local, single-user application**. It does not include:

- Authentication or authorization
- HTTPS/TLS (relies on reverse proxy in production)
- Rate limiting

Security measures in place:

- Path traversal protection on file operations
- Input validation via Pydantic schemas
- SQL injection prevention via SQLAlchemy ORM
- Secret key loaded from `pass` (password store) in production
- Gitleaks pre-commit hook to prevent secret leaks
- Bandit static analysis in CI and pre-commit
