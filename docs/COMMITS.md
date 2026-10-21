# Commit Message Guide — K.H.A.V.I.S.

This document is the project's source of truth for how to write Git commit
messages. It is referenced from `CONTRIBUTING.md` and reviewed in PRs.

We follow the [Conventional Commits](https://www.conventionalcommits.org/)
specification (v1.0.0). Every commit message MUST use a type prefix from the
list below. The body wraps at 72 columns. The subject line MUST be 72
characters or fewer.

---

## 1. Initial Release Commit (v0.1.0)

This is the commit that introduces the repository. It is intentionally long:
it is the only place where we get to describe the entire project before users
arrive. Use the message below verbatim when you tag `v0.1.0`.

```
feat: initial release v0.1.0 - pluggable K.H.A.V.I.S. with multi-agent collaboration

This is the first public release of khavis, a self-hosted, pluggable
router that unifies twelve (and counting) LLM providers behind a single
OpenAI-compatible HTTP API. The release ships the full vertical slice:
plugin discovery, capability-based smart routing, hot-reloadable YAML
configuration, a LangGraph-powered multi-agent orchestrator with three-tier
memory, an append-only attribution log, multi-arch Docker images, and a
green CI/CD pipeline on GitHub Actions.

Highlights:

- 12 LLM provider plugins out of the box: MiniMax-M3, Zhipu GLM-5.3,
  Google Gemini Flash + Pro, NVIDIA Cloud (NIM),
  ByteDance Volcano Ark (DeepSeek / Qwen / Doubao), OpenRouter Free tier,
  OpenAI Platform API (BYOK), Anthropic Claude API (BYOK), and Ollama
  (local + surface). Every plugin ships with a unit test and a
  capability-tag declaration.

- Pluggable ProviderPlugin architecture with file-based auto-discovery.
  Drop a Python file into providers/, list it in pools.yaml, and the
  registry picks it up on next reload. No central registration code.

- Capability-based smart routing. Requests declare a capability
  (code, vision, long-context, cheap, local, ...) and the router picks
  the best pool from prefer/fallback/forbid/require lists, applies
  cost caps, and silently fails over when a pool saturates or returns
  429/503/timeout.

- YAML-driven configuration with hot-reload. Edit
  config/capabilities.yaml or config/pools.yaml, save the file, and the
  running daemon picks up the change via a watchdog observer - no restart,
  no re-auth, no call-site changes.

- LangGraph multi-agent system. Six node types (Planner, two Coder
  variants, Debate, Critic, Verifier, Learn) compose into Pipeline,
  DAG, and Debate primitives. Per-step capability routing, retry, and
  cost budgets are independent of the parent call.

- Three-layer memory. Working memory lives for one Pipeline.run() call,
  episodic memory persists per session_id in SQLite, and semantic memory
  is pluggable via Chroma / Qdrant / pgvector adapters. Per-request opt-in
  via the memory={...} kwarg.

- Attribution log for responsibility tracking. Every chat, stream, and
  agent step is appended to a daily-rotated JSONL file with timestamp,
  pool, capability, cost_usd, latency_ms, status, and a hashed session_id
  for forensics without leaking PII.

- GitHub Actions CI/CD. Five workflows: test (Python 3.11/3.12 matrix
  on Ubuntu and macOS), lint (ruff + mypy), release (build sdist/wheel
  and publish to PyPI on tag), docker (multi-arch buildx for amd64 and
  arm64, push to ghcr.io), and integration (nightly smoke against live
  providers).

- Multi-arch Docker support. A single Dockerfile ships linux/amd64 and
  linux/arm64 images from GHCR, with the config/ directory mounted so
  keys and routing rules persist across container restarts.

- 148 unit tests passing across core, providers, agents, and config
  layers, with 1 skipped (LangGraph optional dep). Plugin discovery test
  enumerates all 12 pools via respx HTTP mocking.

- Apache 2.0 licensed. Use it commercially, fork it, ship it. See LICENSE.

Breaking changes: N/A - this is the initial release.

Dependencies (runtime): pyyaml, watchdog, openai, anthropic,
google-generativeai, requests, pydantic. Development: pytest, pytest-cov,
ruff, mypy, types-PyYAML, types-requests, build, twine.

Refs: README.md, README.zh-TW.md, INSTALLATION.md, CONTRIBUTING.md,
CHANGELOG.md, BUSINESS_PLAN.md, docs/ARCHITECTURE.md,
docs/PLUGIN_DEVELOPMENT.md, docs/CONFIGURATION.md, docs/FAQ.md,
.github/workflows/, Dockerfile, pyproject.toml, requirements.txt.

Co-Authored-By: Your Name <you@example.com>
```

---

## 2. Subsequent Commit Message Templates

After v0.1.0, every commit message MUST follow one of the templates below.
Pick the closest type. If you cannot, the commit is probably doing too much -
split it.

### 2.1 `feat:` — Adding new feature

**Use when** you add user-visible behaviour: a new CLI subcommand, a new
provider plugin, a new HTTP endpoint, a new agent node, a new memory
backend, or a new config knob.

**Template**

```
feat(<scope>): <imperative summary in <=72 chars>

<One-paragraph motivation: what problem does this solve, who benefits,
and why this approach?>

- <Concrete change 1>
- <Concrete change 2>
- <Concrete change 3>

<Optional: link to issue or design doc>

Refs: #<issue>, docs/<file>.md
```

**Real example from this codebase**

```
feat(providers): add ByteDance Volcano Ark Doubao plugin

Adds a third Volcano Ark sub-model (Doubao 1.5 Pro) tagged general and
vision. Closes the gap left by DeepSeek (code) and Qwen (general) so that
the prefer chain for the vision capability has a Chinese-provider option
without falling back to Gemini.

- New file: providers/volcano_doubao.py
- New pool entry in config/pools.yaml (volcano-ark-doubao)
- New unit test: tests/test_providers_unit.py::test_volcano_doubao_chat
- docs/PLUGIN_DEVELOPMENT.md: example updated

Refs: #42, docs/CONFIGURATION.md
```

### 2.2 `fix:` — Bug fix

**Use when** you correct broken behaviour: a 500 where there should be a
graceful 429, a wrong pool picked, a memory leak, an off-by-one, a missing
`await`, a regression caught by a test you added in the same commit.

**Template**

```
fix(<scope>): <imperative summary in <=72 chars>

<What was broken, how it manifested, and how you verified the fix.>

- <Root cause>
- <The change that fixes it>
- <Test that would have caught this>

Fixes #<issue>
```

**Real example from this codebase**

```
fix(router): honour cooldown when pool returns 503 instead of 429

Previously the cooldown window was only triggered on HTTP 429. Pools
behind ByteDance Volcano Ark and NVIDIA NIM routinely return 503 during
sustained load, and without cooldown those pools kept getting picked
and timing out, burning ~6 seconds per request.

- core/capability_router.py: extend retry_on classifier to include 503
- Add regression test asserting 503 triggers cooldown_seconds
- Bump default cooldown_seconds from 30 to 60 in capabilities.yaml

Verified locally: 503s now drop to floor within 2 retries, average
latency under load drops from 8.1s to 1.4s.

Fixes #58
```

### 2.3 `docs:` — Documentation only

**Use when** the diff touches only Markdown, reST, docstrings, or comments.
No production code or test code changes.

**Template**

```
docs(<scope>): <imperative summary in <=72 chars>

<What readers gain and why now.>

- <Doc file or section changed>
- <Doc file or section changed>

Refs: #<issue>
```

**Real example from this codebase**

```
docs(readme): add Local-first quickstart to README

The "Local Ollama with cloud fallback" flow is the most common
support question on Discussions but it lived only in docs/FAQ.md. New
section under "Basic usage" links the FAQ and adds a 6-line code sample.

- README.md: new section 6 (Local-first with cloud fallback)
- README.zh-TW.md: same section in Traditional Chinese
- docs/FAQ.md: link anchor for back-reference

Refs: #31
```

### 2.4 `refactor:` — Code restructure without feature change

**Use when** you reorganise code to make it clearer, faster, or easier to
extend, but you are NOT changing observable behaviour. If a test changes,
it should be because the test is now redundant, not because behaviour
changed.

**Template**

```
refactor(<scope>): <imperative summary in <=72 chars>

<Why the current shape is a problem and what this unlocks.>

- <Move / extract / rename>
- <Move / extract / rename>
- <Behaviour-equivalence note: "all 132 unit tests still pass">

Refs: #<issue>
```

**Real example from this codebase**

```
refactor(registry): extract plugin discovery into PluginLoader

The registry was doing too much: file walking, import, instantiation,
validation, and capability merging were all inline in PluginRegistry.discover.
Splitting discovery into PluginLoader lets the daemon warm-load at startup
without blocking on slow imports and lets tests stub discovery cleanly.

- core/plugin_loader.py: new module with discover() and _safe_import()
- core/registry.py: now delegates to PluginLoader
- tests/test_registry.py: parametrize over loader error paths
- No public API change; all 132 tests still pass.

Refs: #47
```

### 2.5 `test:` — Adding tests

**Use when** you add tests without changing production code, or you fix
a flaky test. If you change production code in the same commit to make
the test pass, this is `fix:` or `feat:`, not `test:`.

**Template**

```
test(<scope>): <imperative summary in <=72 chars>

<What was untested and why it matters.>

- <New test file or test function>
- <New test file or test function>

Refs: #<issue>
```

**Real example from this codebase**

```
test(router): add property-based test for capability fallback chain

Hypothesis-driven tests in tests/test_capability_router.py now generate
random prefer/fallback orderings and assert that the router always picks
the lowest-cost healthy pool within budget. Caught a latent bug where
forbid and require semantics interacted incorrectly when the same pool
appeared in both lists.

- tests/test_capability_router.py: add test_fallback_property
- Adds hypothesis as a test extra in pyproject.toml

Refs: #63
```

### 2.6 `chore:` — Maintenance

**Use when** the change is invisible to users but keeps the repo healthy:
dependency bumps (without behaviour change), lockfile updates, dead-code
removal, formatting-only changes, repo meta tweaks (`.gitignore`,
`.dockerignore`, label taxonomy).

**Template**

```
chore(<scope>): <imperative summary in <=72 chars>

<Why this is needed now.>

- <Change>
- <Change>

Refs: #<issue>
```

**Real example from this codebase**

```
chore(deps): bump pydantic to >=2.7 for improved discriminated-union perf

No behaviour change; pydantic 2.7 ships a 15-20% speedup on the union
discriminator path that we exercise in ChatResponse parsing.

- pyproject.toml: bump lower bound
- requirements.txt: pin for the lockfile check
- CI green on 3.11 and 3.12

Refs: #71
```

### 2.7 `perf:` — Performance improvement

**Use when** the diff is justified by a measurable speedup, memory drop,
or cost reduction. Include the benchmark or before/after numbers in the
body.

**Template**

```
perf(<scope>): <imperative summary in <=72 chars>

<Measured before / after, methodology, and what stays the same.>

- <Optimisation>
- <Optimisation>

Refs: #<issue>
```

**Real example from this codebase**

```
perf(router): cache capability-to-pool resolution per request

The capability resolver was rebuilding the prefer/fallback merge list
on every chat() call, which dominates wall-clock for sub-second
prompts. Caching per (capability, config_version) tuple cuts p50
latency from 38ms to 6ms with no behaviour change.

- core/capability_router.py: add _resolve_cache with LRU(256)
- Invalidate on hot-reload via config_version bump
- Benchmark in docs/ARCHITECTURE.md updated

Refs: #55
```

### 2.8 `ci:` — CI/CD changes

**Use when** the diff is exclusively in `.github/workflows/`,
`Dockerfile`, build scripts, or CI config files. If you change
application code in the same commit, prefix with `ci:` and append
`feat:` / `fix:` in the body, or split.

**Template**

```
ci(<scope>): <imperative summary in <=72 chars>

<What pipeline now does and why.>

- <Workflow file change>
- <Workflow file change>

Refs: #<issue>
```

**Real example from this codebase**

```
ci(docker): add arm64 build to multi-arch matrix

Single-arch images broke Apple-silicon and Graviton users running
khavis on the same hardware as their dev machine. Adding
linux/arm64 to the docker.yml buildx step doubles build time
(~6m -> ~12m) but unblocks the most common homelab topology.

- .github/workflows/docker.yml: extend platforms list
- Dockerfile: ensure wheels are multi-arch safe (verified by
  building on an M3 runner)
- README.md: installation note about arch auto-detection

Refs: #49
```

---

## 3. Style Guide (apply to every type)

| Rule | Rationale |
| --- | --- |
| Subject line <= 72 chars | Renders cleanly in `git log --oneline`, GitHub PR lists, and email clients. |
| Imperative mood ("add", not "added") | Matches Git's own generated messages (`Merge`, `Revert`, `Release`). |
| No trailing period on subject | Convention; saves 1 char and matches the Git source tree. |
| Body wrapped at 72 cols | Forces reviewers to read in narrow columns. |
| Body separated from subject by blank line | Required by Conventional Commits; some tooling (release-please, semantic-release) parses on this. |
| Reference issues as `#123` | GitHub and most tooling auto-link. |
| Reference PRs as `#123` once merged | Same. |
| Use bullet points for multiple changes | Reviewers skim before they read. |
| Mark breaking changes with `!` and a `BREAKING CHANGE:` footer | Required by Conventional Commits; surfaced by release tooling. |
| Avoid emoji in commit bodies | Emoji render inconsistently in `git log` and email; reserve for PR descriptions. |
| Co-author trailers at the very end | Keeps `git shortlog` and `git log --author` clean. |

### 3.1 Breaking change footer

When a commit introduces a breaking change, append a `BREAKING CHANGE:` footer
and bump the type with `!`:

```
feat(router)!: drop support for Python 3.10

Pydantic v2.8 and httpx 0.28 both dropped 3.10 support in their
latest releases, and maintaining compatibility with two diverging
dependency trees is no longer worth the cost. We will keep a
3.10-compatible branch for enterprise users until 2027-Q1.

- pyproject.toml: requires-python bumped to >=3.11
- Dockerfile: base image bumped to python:3.11-slim
- README.md: installation note updated
- .github/workflows/test.yml: matrix narrowed to 3.11 + 3.12

BREAKING CHANGE: Python 3.10 is no longer supported. Users on 3.10
must upgrade before pulling this release. See MIGRATION.md for a
step-by-step guide.

Refs: #88
```

### 3.2 Co-author trailers

When you pair, prompt, or otherwise collaborate, append a trailer block:

```
feat(agents): add Verifier node with self-consistency check

... (body) ...

Co-Authored-By: Your Name <you@example.com>
Co-Authored-By: Reviewer Name <reviewer@example.com>
```

### 3.3 Revert format

When reverting, prefix with `revert:` and reference the SHA being reverted:

```
revert: feat(providers): add ByteDance Volcano Ark Doubao plugin

This reverts commit 1a2b3c4d5e6f. The Doubao endpoint requires an
account-level allow-list we cannot satisfy in CI, and the integration
test fails on every PR. We will reintroduce once the provider opens
public access.

Refs: #42, #99
```

---

## 4. Quick reference card

```
<type>(<scope>): <subject>            # subject <= 72 chars, imperative, no period

<body wrapped at 72 cols>             # why, not what; bullets for lists

<footer>                              # Refs: #1, BREAKING CHANGE:, Co-Authored-By:
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`,
`build`, `revert`.

When in doubt, look at the last 20 commits with `git log --oneline -n 20`
and match the dominant pattern in that area of the codebase.
