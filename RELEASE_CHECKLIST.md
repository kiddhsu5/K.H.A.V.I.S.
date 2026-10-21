# K.H.A.V.I.S. v0.1.0 Release Checklist

> **Operational playbook** for taking K.H.A.V.I.S. from "ready in local repo" to "publicly available on GitHub + PyPI + Docker Hub + Hacker News".
> Use this as a literal checklist — every item is something a solo maintainer has personally forgotten at least once.
> Format: T-X days, counting down to launch (T-0).

**Project:** K.H.A.V.I.S. (Apache-2.0, plugin-based router for 12 LLM providers)
**Author:** kiddhsu5 (solo developer, placeholder)
**Target launch:** late September 2026 (Tuesday or Wednesday recommended for HN timing)
**Channels:** GitHub, PyPI, Docker Hub, GitHub Container Registry, Hacker News, Twitter/X, dev.to, Zhihu / 知乎, V2EX, r/LocalLLaMA, r/Python, r/MachineLearning, Lobsters, 掘金
**Baseline:** 84 files, 14,200 lines, 148 tests passing, 12 plugins verified, 0 critical CVEs

---

## Quick-reference timeline

| Phase | Window | Focus |
|-------|--------|-------|
| Phase 0 | T-14 to T-7 days | Repo housekeeping, accounts, legal |
| Phase 1 | T-7 to T-1 day | Final QA, dry-runs, secrets, first release commit |
| Phase 2 | T-0 (launch day) | Publish, announce, monitor |
| Phase 3 | T+1 to T+7 days | Triage, hotfix, retrospective |
| Phase 4 | T+30 / T+60 / T+90 | Milestone reviews, SaaS decision |

---

## Phase 0: Pre-Preparation (T-14 to T-7 days)

### Repo housekeeping

- [ ] `git init` if not already initialized
- [ ] `.gitignore` configured (covers `.env`, `__pycache__/`, `*.egg-info/`, `.venv/`, `audit/`, `dist/`, `.DS_Store`)
- [ ] `.dockerignore` configured (excludes `tests/`, `docs/`, `.github/`, `*.md` except `README.md`)
- [ ] All 82 source files committed (no untracked files: `git status` clean)
- [ ] Default branch renamed to `main` (not `master`)
- [ ] Branch protection rules drafted (but **not yet applied** — see Phase 1)

### Legal

- [ ] Apache-2.0 `LICENSE` present and verified (`head -1 LICENSE`)
- [ ] `NOTICE` file present if using third-party brand names (OpenAI, Anthropic, Google, etc. — they are referenced in plugins)
- [ ] No proprietary code, no GPL/LGPL dependencies introduced
- [ ] `SECURITY.md` written (private disclosure email configured — see template in this PR)
- [ ] `CODE_OF_CONDUCT.md` present (Contributor Covenant v2.1)

### Accounts setup

- [ ] **GitHub** — account created, 2FA enabled (TOTP preferred over SMS)
- [ ] **GitHub org/repo** — `github.com/kiddhsu5/K.H.A.V.I.S.` created (public)
- [ ] **PyPI** — account created at pypi.org, 2FA mandatory since 2024
- [ ] **TestPyPI** — account created at test.pypi.org for dry-runs
- [ ] **Docker Hub** — `kiddhsu` namespace reserved
- [ ] **GitHub Container Registry (GHCR)** — enabled at repo settings
- [ ] **GitHub Sponsors** — account enabled (Apache 2.0 / no SaaS tier; see `docs/STRATEGY.md` §7.2 — do not open Stripe)
- [ ] **Twitter/X** — @kiddhsu handle confirmed, bio updated
- [ ] **dev.to** — account created, profile photo + bio
- [ ] **Hacker News** — account with > 5 karma (so you can submit Show HN without delay)
- [ ] **LinkedIn** — profile updated with "open-source maintainer" line

### Domain / branding (optional)

- [ ] `khavis.example.com` registered (or `khavis.io`) — skip if cost-prohibitive; PyPI + GitHub are sufficient
- [ ] Logo / wordmark designed (Figma, or use a public-domain glyph like `→`)
- [ ] Brand colors picked (we use a single accent — `#0EA5E9` sky-500 — in README)

### Documentation skeleton

- [ ] `README.md` proofread (361 lines, already drafted)
- [ ] `README.zh-TW.md` proofread (361 lines, already drafted)
- [ ] `CONTRIBUTING.md` proofread (247 lines, already drafted)
- [ ] `docs/ARCHITECTURE.md` proofread (14,074 bytes, already drafted)
- [ ] `docs/PLUGIN_DEVELOPMENT.md` proofread (10,496 bytes, already drafted)
- [ ] `docs/CONFIGURATION.md` proofread (8,157 bytes, already drafted)
- [ ] `docs/FAQ.md` proofread (8,092 bytes, already drafted)

---

## Phase 1: Final Pre-Launch (T-7 to T-1 day)

### Code quality final pass

- [ ] Run `python3 -m pytest tests/ -v` — target **148+ passing, 0 failing**
- [ ] Run `python3 scripts/test_plugins.py` — expect **12 plugins verified**
- [ ] Run `python3 scripts/integration_test.py` with all env vars set — target **12/12 passing** (BYOK pools skipped if env unset)
- [ ] Run `ruff check .` — expect **0 errors** (warnings allowed, document in `# noqa` if false-positive)
- [ ] Run `mypy core/ providers/` — expect **0 errors** (strict mode optional for first release)
- [ ] Verify test coverage: `pytest --cov=core --cov=providers --cov-report=term-missing`
  - [ ] `core/` ≥ 80% coverage
  - [ ] `providers/` ≥ 60% coverage
- [ ] No TODO/FIXME left in shipped code paths (`grep -r "TODO\|FIXME" core/ providers/ | grep -v ".pyc"`)

### Documentation final review

- [ ] Every `docs/*.md` linked from main README (manual check: grep `docs/` in `README.md`)
- [ ] `CHANGELOG.md` has dated `## [0.1.0] — 2026-09-XX` section
- [ ] All code examples in README actually run (no dead snippets)
- [ ] All badge URLs in README point to real shields.io endpoints
- [ ] Hero ASCII diagram renders in monospace preview
- [ ] No broken internal links (`markdown-link-check README.md docs/*.md`)

### Docker test

- [ ] `docker build -t khavis:test .` succeeds on **arm64** (Apple Silicon)
- [ ] `docker build -t khavis:test-amd .` succeeds on **amd64** (cloud runner or `docker buildx build --platform linux/amd64`)
- [ ] `docker run --rm khavis:test python3 scripts/test_plugins.py` — 12 plugins verified inside container
- [ ] `docker run --rm -p 8080:8080 khavis:test` — health endpoint responds on `http://localhost:8080/health`
- [ ] Image size < 300 MB (`docker images khavis:test` — verify slim base)

### PyPI dry-run

- [ ] `python3 -m pip install --upgrade build twine`
- [ ] `python3 -m build --sdist --wheel` — both `dist/*.whl` and `dist/*.tar.gz` produced
- [ ] `twine check dist/*` — `PASSED` for both files
- [ ] Upload to TestPyPI: `twine upload --repository testpypi dist/*`
- [ ] Verify install: `pip install --index-url https://test.pypi.org/simple/ K.H.A.V.I.S.`
- [ ] Run `khavis --version` from the TestPyPI install — expect `0.1.0`

### Secrets configuration

- [ ] **GitHub repo secrets** (Settings → Secrets and variables → Actions):
  - [ ] `PYPI_API_TOKEN` — set, OR configure **trusted publishing** (OIDC) per https://docs.pypi.org/trusted-publishers/
  - [ ] `DOCKERHUB_USERNAME` — `kiddhsu`
  - [ ] `DOCKERHUB_TOKEN` — generated at hub.docker.com → Account Settings → Security
  - [ ] `INTEGRATION_OPENAI_KEY` — optional, for nightly integration tests
  - [ ] `INTEGRATION_ANTHROPIC_KEY` — optional
  - [ ] `INTEGRATION_GEMINI_KEY` — optional
- [ ] **GitHub branch protection on `main`**:
  - [ ] Require pull request reviews before merging (1 approval minimum)
  - [ ] Require status checks to pass before merging (CI must be green)
  - [ ] Require linear history (no merge commits)
  - [ ] Include administrators (apply rules to yourself — yes, even solo)
  - [ ] Allow force pushes: **disabled**
  - [ ] Allow deletions: **disabled**

### First release commit

- [ ] Stage all files: `git add -A`
- [ ] Verify staged diff: `git diff --cached --stat` — should show README, CHANGELOG, docs/, .github/, source files
- [ ] Use commit message from `docs/COMMITS.md` (or, if missing, follow Conventional Commits):
  ```
  chore(release): v0.1.0 — initial public release

  - 11 verified LLM provider plugins
  - 132 passing tests
  - Capability-based routing (prefer/fallback/forbid/require)
  - Hot-reloadable YAML config
  - Multi-agent primitives (Pipeline, DAG, Debate)
  ```
- [ ] Commit signed: `git commit -S -m "..."`
- [ ] Tag signed: `git tag -s v0.1.0 -m "v0.1.0 — initial public release"`
- [ ] Verify tag signature: `git tag -v v0.1.0`
- [ ] Push branch: `git push origin main`
- [ ] Push tag: `git push origin v0.1.0` — **this triggers the release workflow**

### Final sanity checks (T-1 day, evening)

- [ ] `git log --oneline -10` — history clean, no "wip" commits
- [ ] `git tag --list` — `v0.1.0` present, signed
- [ ] GitHub Actions green: `https://github.com/kiddhsu5/K.H.A.V.I.S./actions`
- [ ] TestPyPI install command tested one more time
- [ ] Docker image built and tested one more time
- [ ] Phone silenced, calendar blocked 9 AM–noon tomorrow for launch
- [ ] Go to bed at a reasonable hour

---

## Phase 2: Launch Day (T-0)

> **Recommended launch window:** Tuesday or Wednesday, 9 AM US Eastern (= 9 PM UTC+8 Taiwan / 6 AM Pacific).
> This catches both Asia evening and US morning traffic on HN.
> Avoid Mondays (people triage weekend backlog), Fridays (people leave early), and weekends (low HN traffic).

### Morning (your local 9 AM, ~UTC+8)

- [ ] Verify **GitHub Actions passed** on the `v0.1.0` tag push
  - [ ] `release.yml` job: `build` → green
  - [ ] `release.yml` job: `publish-pypi` → green (check PyPI page in 5 min)
  - [ ] `release.yml` job: `github-release` → green
  - [ ] `docker.yml` job: multi-arch build → green (arm64 + amd64)
- [ ] Verify **PyPI package visible** at https://pypi.org/project/khavis/
  - [ ] Version `0.1.0` listed
  - [ ] Description rendered
  - [ ] `pip install khavis` works in a fresh venv
- [ ] Verify **Docker image pushed to GHCR** at https://github.com/kiddhsu5/K.H.A.V.I.S./pkgs/container/khavis
  - [ ] Tags: `latest`, `0.1.0`, `v0.1.0`, `sha-<short>`
- [ ] Verify **Docker image pushed to Docker Hub** at https://hub.docker.com/r/kiddhsu/khavis
  - [ ] Tags: `latest`, `0.1.0`
- [ ] Verify **GitHub Release published** at https://github.com/kiddhsu5/K.H.A.V.I.S./releases/tag/v0.1.0
  - [ ] Release notes auto-generated from CHANGELOG
  - [ ] Wheel + sdist attached as binaries

### Mid-morning

- [ ] Draft announcement posts in scratch buffer (use `blog/` drafts):
  - [ ] `blog/twitter-thread.md` (237 lines, ready)
  - [ ] `blog/show-hn-post.md` (98 lines, ready)
  - [ ] `blog/dev-to-post.md` (459 lines, ready)
  - [ ] `blog/zhihu-post.md` (804 lines, ready)
- [ ] Pin a tweet: "K.H.A.V.I.S. v0.1.0 is out → https://github.com/kiddhsu5/K.H.A.V.I.S."

### Afternoon (US time = your evening)

- [ ] **Submit Show HN** at 9:00 AM ET sharp (set an alarm)
  - [ ] Title: `Show HN: K.H.A.V.I.S. – One endpoint for 12 LLM providers (BYOK)`
  - [ ] URL: `https://github.com/kiddhsu5/K.H.A.V.I.S.`
  - [ ] First comment: pre-written technical depth (use `blog/show-hn-post.md` first comment block as base)
  - [ ] Tag: `python`, `open-source`, `llm`, `ai-infrastructure`
- [ ] **Post Twitter thread** at the same instant (within 5 min of HN submission)
  - [ ] First tweet: tagline + link
  - [ ] 7-tweet arc: problem → solution → demo → architecture → who-cares → CTA
  - [ ] Final tweet: "HN discussion → " with link
- [ ] **Cross-post to dev.to** (use `blog/dev-to-post.md` as base, add cover image)
- [ ] Reply to every HN comment within 2 hours while it's on the front page

### Evening

- [ ] **Submit to subreddits** (stagger by 2 hours each to avoid spam-detection):
  - [ ] r/LocalLLaMA — title: `Show: K.H.A.V.I.S. — one endpoint for 12 LLM providers (BYOK)`, link-only post
  - [ ] r/MachineLearning — title: `[P] K.H.A.V.I.S. — open-source router for 12 LLM providers with capability-based dispatch`
  - [ ] r/Python — title: `Show & Tell: K.H.A.V.I.S. v0.1.0 — plugin-based LLM gateway (Apache 2.0)`
  - [ ] Lobsters — submit to `python` tag (requires invite)
- [ ] **Submit to Chinese-language communities**:
  - [ ] V2EX — `创造` node, title: `开源 K.H.A.V.I.S. v0.1.0: 一個 endpoint 串接 12 個 LLM 服務`
  - [ ] 掘金 (`juejin.cn`) — `后端` tag, cross-post from `blog/zhihu-post.md`
  - [ ] 知乎 (`zhihu.com`) — answer in `LLM 工具` topic, link to GitHub
- [ ] **Hacker News monitoring**: stay online until HN falls off front page (~24h)
- [ ] Reply to every GitHub issue opened today, even if it's "thanks, will look"

### End of day (T-0, your midnight)

- [ ] Snapshot stats: stars, PyPI downloads, Docker pulls, HN points, Twitter impressions
- [ ] Write a private diary entry: "what surprised me today"
- [ ] Sleep

---

## Phase 3: Post-Launch (T+1 to T+7 days)

### Day 1 (T+1)

- [ ] Respond to **all HN comments within 2 hours** during HN traffic window
- [ ] Triage **every new GitHub issue** opened in the last 24h:
  - [ ] Apply labels: `bug` / `enhancement` / `question` / `docs` / `good first issue`
  - [ ] Assign milestone if known (`v0.1.1` for quick fixes, `v0.2.0` for features)
  - [ ] Reply with acknowledgment within 24h even if fix is not ready
- [ ] Monitor **PyPI download stats** at https://pypistats.org/packages/khavis
- [ ] Monitor **Docker pull stats** at https://hub.docker.com/r/kiddhsu/khavis
- [ ] Review any **security disclosures** via private email — if any, follow `SECURITY.md`

### Day 2-3 (T+2 to T+3)

- [ ] Fix any **critical bugs** reported (Sev 1, see OPERATIONS.md)
- [ ] Cut **v0.1.1** hotfix release if needed:
  - [ ] `git checkout v0.1.0 -b hotfix/v0.1.1`
  - [ ] Apply fix, commit, tag `v0.1.1`, push — auto-publishes via release.yml
- [ ] **First retrospective** (private, in `memory/` directory):
  - [ ] What went well
  - [ ] What went poorly
  - [ ] Top 3 user requests
  - [ ] Top 3 confusion points in HN/Reddit comments
  - [ ] Calibrated expectation vs. reality (stars, downloads)

### Day 7 (T+7)

- [ ] **Public retrospective post** on dev.to: "What I learned launching K.H.A.V.I.S. v0.1.0"
- [ ] Update `CHANGELOG.md` with what was learned
- [ ] **Plan v0.2.0 features** based on top community requests
- [ ] Open **5 labelled issues** for v0.2.0 candidates (RFCs)
- [ ] Thank early contributors in a Twitter thread (if any PRs merged)

---

## Phase 4: 30 / 60 / 90 Day Milestones

### T+30 days — first month

- [ ] **Quantitative:**
  - [ ] 100+ GitHub stars
  - [ ] 10+ GitHub issues opened (mix of bugs + features)
  - [ ] 1+ external PR merged (any size counts)
  - [ ] 500+ PyPI lifetime downloads
  - [ ] 100+ Docker pulls
- [ ] **Qualitative:**
  - [ ] At least one substantive blog post / tutorial written by an external user
  - [ ] No Sev 1 security issues unresolved
  - [ ] Maintainer response time median < 48 hours
- [ ] **Actions:**
  - [ ] Cut v0.2.0 release
  - [ ] Submit to awesome-python list (PR to https://github.com/vinta/awesome-python)
  - [ ] Submit to ProductHunt (optional, see Day 14)

### T+60 days — second month

- [ ] **Quantitative:**
  - [ ] 500+ GitHub stars
  - [ ] 50+ PyPI downloads/day average
  - [ ] 50+ closed issues
  - [ ] 5+ external contributors
- [ ] **Qualitative:**
  - [ ] GitHub Discussions active (>10 threads with maintainer participation)
  - [ ] Discord server (or Discussions-only) — decide based on traffic
  - [ ] Positive sentiment in feedback (sample 10 issues, 8+ positive)
- [ ] **Actions:**
  - [ ] Plan v0.3.0 with backward-incompatible features (semver bumps)
  - [ ] Write first sponsor prospectus (if considering GitHub Sponsors)

### T+90 days — quarter

- [ ] **Quantitative:**
  - [ ] 1,000+ GitHub stars
  - [ ] 100+ PyPI downloads/day average
  - [ ] 10+ external contributors (any PR count)
  - [ ] 100+ closed issues
- [ ] **Qualitative:**
  - [ ] Active community discussions (>50 threads)
  - [ ] Self-sustaining contributor pipeline (3+ recurring contributors)
  - [ ] Clear product-market fit signal (users report cost savings, quota wins)
- [ ] **Business:**
  - [ ] Decide on **Pro tier SaaS launch** (managed K.H.A.V.I.S. hosted)
  - [ ] First paying customer (if SaaS path taken)
  - [ ] Or: apply for OSS grants (GitHub Sponsors, OpenAI credits, etc.)

---

## Failure Modes & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Nobody shows up on HN** | Medium | Low | Pre-schedule Twitter, dev.to, and Reddit posts so launch isn't HN-or-bust |
| **Too much HN traffic, site crashes** | Low | Medium | GitHub Pages static, no server-side load; PyPI handles their own |
| **Critical bug at launch** | Medium | High | v0.1.1 hotfix procedure documented (Day 2-3); branch protection catches most |
| **Competitor launches similar tool** | High | Low | Focus on community, ship v0.2.0 faster than they ship |
| **Security issue reported** | Low | Critical | Private disclosure via SECURITY.md; private email + GitHub Security Advisories |
| **Maintainer burnout** | Medium | High | Set clear "response within 48h" expectation; no on-call; block weekends |
| **Brand-name DMCA complaint** | Low | Medium | NOTICE file attributes all trademarks; polite takedown process |
| **PyPI name squatted** | Very Low | Critical | Verify `pip install khavis` works 7 days before launch (TestPyPI dry-run) |
| **GitHub org name squatted** | Very Low | Critical | Reserve `kiddhsu/khavis` 14 days before launch |

---

## Success Criteria at 90 Days

### Quantitative

- [ ] **1,000+** GitHub stars
- [ ] **50+** PyPI downloads/day average
- [ ] **100+** closed issues
- [ ] **10+** external contributors (any PR count)
- [ ] **5,000+** Docker pulls (cumulative)

### Qualitative

- [ ] Active community discussions (Discussions or Discord)
- [ ] Self-sustaining contributor pipeline (recurring contributors)
- [ ] Positive sentiment in feedback (>80% positive in sampled issues)
- [ ] Clear product-market fit signal (users cite cost savings, uptime wins)
- [ ] At least one production deployment story from a real company

---

## Appendix A: Communication Templates

### Show HN first comment template

```
Thanks for checking this out. A few notes for anyone evaluating it:

1. **Why BYOK**: Most "AI gateways" proxy your keys and bill you markup.
   khavis uses your keys directly — no middleman, no markup, no
   quota-sharing with strangers.

2. **Why capability routing**: Instead of "always use GPT-4", you declare
   what you need (`prefer: code`, `fallback: cheap`) and the router
   picks from your pools. Works like DNS, but for LLMs.

3. **Why hot reload**: Edit `pools.yaml` while the server is running.
   No restart, no dropped requests.

4. **What's next**: Multi-provider load balancing (v0.2.0), semantic
   caching (v0.2.0), cost analytics (v0.3.0).

AMA in the comments. — Kidd
```

### Bug-triage response template

```
Thanks for the report! Reproducing now. Could you paste:

1. Output of `khavis --version`
2. The exact command that failed
3. The full traceback (if any)
4. Your `pools.yaml` (redact keys)

Will triage within 24h.
```

### Hotfix announcement template (Twitter)

```
v0.1.1 just shipped — fixes [issue #N] where [one-sentence symptom].
Upgrade with `pip install --upgrade khavis` or pull `:0.1.1` from
Docker Hub. No breaking changes. Thanks to @<reporter> for the report.
```

---

## Appendix B: Files in this release

| Path | Lines | Purpose |
|------|-------|---------|
| `core/` | ~3,200 | Router, registry, hot reload, audit log |
| `providers/` | ~2,100 | 12 plugin implementations |
| `tests/` | ~3,400 | 148 tests, contract + integration |
| `docs/` | ~3,800 | Architecture, config, plugin dev, FAQ |
| `blog/` | ~3,200 | HN post, dev.to, twitter thread, zhihu, etc. |
| `scripts/` | ~600 | Plugin test, integration test, start.sh |
| `config/` | ~250 | capabilities.yaml, pools.yaml, examples |
| `examples/` | ~600 | 10 worked examples (basic → multi-agent) |
| `agents/` | ~700 | Pre-baked agent JSON files (Pipeline/DAG/Debate) |
| Root + meta | ~600 | README, CHANGELOG, LICENSE, pyproject, Dockerfile |

---

## Appendix C: Day-of checklist (print this out)

```
□ 09:00  Verify GitHub Actions green on tag v0.1.0
□ 09:05  Verify PyPI shows khavis 0.1.0
□ 09:10  Verify GHCR + Docker Hub images pushed
□ 09:15  Verify GitHub Release page published
□ 09:30  Pin tweet drafted
□ 09:45  HN submission tab open in browser
□ 10:00  Submit Show HN at 9 AM ET (= 13:00 UTC)
□ 10:01  Post Twitter thread
□ 10:05  Post dev.to
□ 10:30  Submit to r/LocalLLaMA
□ 12:30  Submit to r/MachineLearning
□ 14:30  Submit to r/Python
□ 15:00  Submit to Lobsters (if approved)
□ 21:00  Submit to V2EX
□ 21:30  Submit to 掘金
□ 22:00  Submit to 知乎
□ 23:59  Snapshot stats, sleep
```

---

**End of checklist.** When every box above is ticked, K.H.A.V.I.S. v0.1.0 is live.
