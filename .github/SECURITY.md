# Security Policy

> K.H.A.V.I.S. 是由 kiddhsu5 個人維護的開源專案,我們非常重視安全問題。本文件說明如何回報漏洞、預期的回應時間,以及我們對資訊透明度的承諾。
> The K.H.A.V.I.S. maintainers take security seriously. This document explains how to report vulnerabilities, what to expect from us, and how we credit reporters.

---

## Supported Versions

下表列出目前受到安全更新支援的版本。建議所有使用者升級至最新版本。
The following versions of K.H.A.V.I.S. currently receive security updates. We strongly recommend staying on the latest release.

| Version | Supported          | Notes |
|---------|--------------------|-------|
| 0.1.x   | :white_check_mark: | Active development — patches shipped within 30 days |
| 0.0.x   | :x:                | Pre-release — please upgrade to 0.1.0 |
| < 0.1.0 | :x:                | Never publicly released |

> 我們採用 [Semantic Versioning](https://semver.org/):major version bumps indicate breaking changes, patch versions are reserved for bug fixes and security updates.

---

## Reporting a Vulnerability

### 請勿透過公開 GitHub Issue 回報安全漏洞。Please do NOT report security vulnerabilities via public GitHub issues.

We offer **two private channels** for disclosure. Use whichever you are most comfortable with.

### Channel 1: GitHub Security Advisories (preferred)

開啟一個 private security advisory:
1. 前往 https://github.com/kiddhsu5/K.H.A.V.I.S./security/advisories/new
2. 填寫漏洞詳情 (影響範圍、重現步驟、概念驗證)
3. 提交後只有 maintainer 與 GitHub 信任的通報者會看到內容

This is the preferred channel because:
- All communication stays within GitHub
- We can collaborate on a fix in a private fork
- CVE is auto-published when the advisory is closed

### Channel 2: Private email

寄信至 **kiddhsu5@users.noreply.github.com**

Subject line format: `[K.H.A.V.I.S. security] <short description>`

Please encrypt sensitive details using our PGP key:

```
-----BEGIN PGP PUBLIC KEY BLOCK-----

mDMEarTYwBYJKwYBBAHaRw8BAQdA3iXG+B/CBoyjfeW7uCKm5FtJlQ4mtXuEXw3w
8StLB1C0I0hzdSBDaGluLVl1YW4gPGtpZGQuaHN1QGljbG91ZC5jb20+iK8EExYK
AFcWIQQP/i1wRKJs09K47O0c7Wcf9TaobwUCarTYwBsUgAAAAAAEAA5tYW51Miwy
LjUrMS4xMiwwLDMCGwMFCwkIBwICIgIGFQoJCAsCBBYCAwECHgcCF4AACgkQHO1n
H/U2qG/ZiwD8DisoCrBynsOFEsUGmY2qHTBJC7km0xwoRPMeaRkXDpkBAJ05pEDt
urUFpPbWn2ltew5T0bPH7NDkqZUTmvVZYNQNuDgEarTYwBIKKwYBBAGXVQEFAQEH
QO4nHsiq+g9XdseCa6+xe4frzTA5Sp7SibMYX8cMBEohAwEIB4iUBBgWCgA8FiEE
D/4tcESibNPSuOztHO1nH/U2qG8FAmq02MAbFIAAAAAABAAObWFudTIsMi41KzEu
MTIsMCwzAhsMAAoJEBztZx/1Nqhv5LYA/iSyYWo6bHeih5UoGw4oYhUvNb4kP180
1i0ELug8wRWHAP0eWfiMNQW7w2L7z5QyFmhe2dKmGAqooTh5xNPvLLkeDQ==
=cS6f
-----END PGP PUBLIC KEY BLOCK-----
```

Fingerprint: `0FFE 2D70 44A2 6CD3 D2B8  ECED 1CED 671F F536 A86F`  
(ed25519 sign/cert · cv25519 encrypt)

Full copy: https://khavis.example.com/pgp.txt

### What to include in your report

一個好的漏洞回報應該包含:
A good vulnerability report should include:

1. **Summary** — one-sentence description of the issue
2. **Affected versions** — which versions reproduce the bug
3. **Affected component** — `core/`, `providers/<name>/`, `config/`, or `scripts/`
4. **Reproduction steps** — minimal code or command sequence
5. **Impact** — what an attacker could achieve (data exfiltration, RCE, DoS, etc.)
6. **Environment** — Python version, OS, deployment mode (Docker / native / k8s)
7. **Suggested fix** — optional, but appreciated if you have a patch idea

You can use the template below:

```markdown
## Vulnerability Report

**Summary:**
[one-sentence description]

**Affected versions:** [e.g., 0.1.0]
**Component:** [e.g., providers/openai_compat/chat.py]

**Severity (your estimate):** [Critical / High / Medium / Low]

**Reproduction:**
\`\`\`python
# minimal repro
\`\`\`

**Impact:**
[what an attacker could do]

**Environment:**
- khavis version:
- Python version:
- OS:
- Deployment:
```

---

## Response Timeline

我們承諾以下回應時間。These are targets, not guarantees — but we hit them on >90% of reports.

| Stage | Target | Notes |
|-------|--------|-------|
| **Acknowledgment** | **48 hours** | First reply confirming receipt |
| **Initial triage** | **7 days** | Severity assigned, scope confirmed |
| **Fix in progress** | **30 days** for non-critical, **7 days** for Critical |
| **Coordinated disclosure** | **90 days** maximum | Or sooner if a fix is ready |
| **Public advisory** | On fix release | CVE assigned via GitHub Security Advisories |

If we need more time, we will tell you before the deadline.

---

## Severity Classification

We use CVSS v3.1 informally, but treat severity like this:

### Critical (Sev 1) — fix within 7 days, hotfix release

- Remote code execution via crafted request
- API key exfiltration from process memory or config files
- Authentication bypass
- Supply chain compromise of a published artifact

### High (Sev 2) — fix within 30 days, patch release

- Privilege escalation within the router
- Denial of service via unauthenticated request
- Path traversal in config reload
- SSRF in provider plugins

### Medium (Sev 3) — fix within 90 days, patch release

- Information disclosure (e.g., verbose error messages leaking paths)
- YAML deserialization issues (we use `yaml.safe_load` everywhere — verify)
- Audit log tampering

### Low (Sev 4) — backlog, fix when convenient

- Documentation security issues
- Theoretical issues requiring unlikely conditions
- Issues in disabled-by-default features

---

## Hall of Fame

我們感謝每一位負責任的漏洞通報者。如果您同意,我們會在修復發布後於下方列名。
We thank every responsible reporter. With your permission, we credit you here after the fix ships.

| Date | Reporter | Issue | Severity |
|------|----------|-------|----------|
| _none yet_ | — | — | — |

To be listed, include "credit me as: <name or handle>" in your report. To remain anonymous, say so explicitly.

---

## Scope

### In scope

- `core/` — router, registry, hot-reload, audit log
- `providers/` — all 11 plugin implementations
- `config/` — YAML parsers, validators
- `scripts/start.sh` — the Docker entrypoint
- `Dockerfile` — supply chain of the published image
- Any GitHub Action workflow that runs on PR or release
- PyPI package `khavis` and its dependencies (transitively — please report, but we may redirect to upstream)

### Out of scope

- The 11 LLM provider APIs themselves (report to OpenAI, Anthropic, Google, etc.)
- Third-party dependencies' vulnerabilities (we will file upstream, but they own the fix)
- Test fixtures or example code that requires manual opt-in
- Issues requiring physical access to the host
- Social engineering the maintainer
- Rate-limiting / quota concerns at the provider level

---

## Coordinated Disclosure Best Practices

When you report a vulnerability, we ask that you:

1. **Give us reasonable time** — at least 90 days before public disclosure
2. **Avoid privacy violations** — don't access other users' data, even if you find a way
3. **Don't exploit beyond proof-of-concept** — demonstration is fine, weaponization is not
4. **Keep details confidential** until we publish the advisory

In return, we will:

1. **Credit you** in the advisory and CHANGELOG (if you want)
2. **Keep you informed** of our progress
3. **Not pursue legal action** against good-faith security research
4. **Pay a small bounty** — currently $25–$100 USD via GitHub Sponsors or OpenAI API credits (placeholders for when the project is funded)

---

## Security Update Distribution

Security fixes are published through:

1. **PyPI** — `pip install --upgrade K.H.A.V.I.S.`
2. **GitHub Releases** — tagged with `v0.1.x` and security advisory linked
3. **Docker Hub** — `:0.1.x` and `:latest` tags updated
4. **GHCR** — same tags
5. **CHANGELOG.md** — under a `[Security]` subsection

Watch this repo (click "Watch" → "Custom" → "Security alerts") to receive GitHub Security Advisory notifications.

---

## Contact

- **Private disclosure:** kiddhsu5@users.noreply.github.com (PGP available)
- **GitHub Security Advisories:** https://github.com/kiddhsu5/K.H.A.V.I.S./security/advisories/new
- **General questions:** open a Discussion at https://github.com/kiddhsu5/K.H.A.V.I.S./discussions

Thanks for keeping K.H.A.V.I.S. and its users safe.
