# Security Policy — J.A.R.V.I.S. AI

## Security Principles

J.A.R.V.I.S. AI is built with privacy and safety at its core:
1. **Local Credentials & Secret Safety**: API keys (`config/api_keys.json`) and personal memory stores (`memory/long_term.json`) remain local to your machine and are never transmitted to external telemetry servers.
2. **Redaction**: API keys and tokens are automatically masked in log outputs and UI displays.
3. **Boundary Controls**: File controller and shell automation modules strictly validate path boundaries to prevent traversal attacks.

---

## Supported Versions

| Version | Supported | Security Updates |
| :--- | :--- | :--- |
| `v1.0.x` | Yes | Active |
| `< 1.0.0` | No | End of Life |

---

## Reporting a Vulnerability

If you discover a security vulnerability in J.A.R.V.I.S. AI:

1. **Do NOT** open a public GitHub issue.
2. Report the details directly to the lead security maintainer via email: `ankitpaul6201@gmail.com`.
3. Include a detailed reproduction script, affected component name, and impact assessment.

### Response Timeline
- **Acknowledgement**: Within 24 hours.
- **Triage & Assessment**: Within 48 hours.
- **Fix & Patch Release**: Within 7 business days.
