# K.H.A.V.I.S. launch checklist

> Pre-launch and post-launch checklists for the public debut of K.H.A.V.I.S. v0.1.0.
> Use this as a literal checklist — every item is something I have personally forgotten at least once.

**Launch date:** 2026-09-20 (Tue)
**Author:** kiddhsu5 (solo)

---

## T-7 days: pre-launch preparation

### Repository hygiene

- [ ] **GitHub repo created** — `kiddhsu/khavis` (public, default branch `main`)
- [ ] **Repo description set** — `One endpoint for 12 LLM providers with zero quota interruption. Apache 2.0.`
- [ ] **Website URL set** — `https://khavis.example.com` (placeholder if no site yet)
- [ ] **Topics set** — `llm`, `openai`, `anthropic`, `router`, `python`, `open-source`, `byok`, `multi-agent`, `capability-routing`
- [ ] **README polished** — title, tagline, badges, quick-start, links, hero ASCII diagram
- [ ] **README.zh-TW.md** translated and synced
- [ ] **CHANGELOG.md** has v0.1.0 entry with date, highlights, breaking changes (none for first release)
- [ ] **LICENSE** present and correct (Apache-2.0)
- [ ] **CONTRIBUTING.md** has a clear PR template and a code-of-conduct link
- [ ] **CODE_OF_CONDUCT.md** present (Contributor Covenant is fine)
- [ ] **SECURITY.md** present, with a private disclosure email
- [ ] **.github/ISSUE_TEMPLATE/bug_report.md** present
- [ ] **.github/ISSUE_TEMPLATE/feature_request.md** present
- [ ] **.github/PULL_REQUEST_TEMPLATE.md** present
- [ ] **.gitignore** covers `.env`, `__pycache__`, `audit/`, `*.egg-info`, `.venv/`
- [ ] **No secrets in git history** — `git log --all -p | grep -i "api_key\|secret\|token" | head` returns nothing
- [ ] **Default branch protection** — require PR review before merge (even for solo dev, this catches mistakes)
- [ ] **README badge for PyPI version** added (will show after first publish)
- [ ] **README badge for Docker pulls** added (will show after first push)

### Code quality

- [ ] **All tests pass** — `pytest -x` exits 0
- [ ] **Type checks pass** — `mypy --strict core/ providers/` exits 0
- [ ] **Lint clean** — `ruff check .` exits 0, `black --check .` exits 0
- [ ] **Test coverage** ≥ 80% for core/, ≥ 60% for providers/
- [ ] **Contract tests** for every provider plugin (chat returns OpenAI-shape; quota returns documented shape; health_check ok/down correctly)
- [ ] **Integration test** with at least one real provider (use a $5 free-tier credit to verify the full path)
- [ ] **Smoke test** — fresh `pip install khavis && khavis init && khavis serve` from a clean venv

### Packaging

- [ ] **pyproject.toml** complete — name, version, description, license, authors, python_requires, dependencies, optional-dependencies, urls
- [ ] **First release tagged** — `v0.1.0` tag created and pushed
- [ ] **GitHub release published** — title `v0.1.0 — initial public release`, body auto-generated from CHANGELOG
- [ ] **PyPI package published** — `python -m build && python -m twine upload dist/*`
  - [ ] Test PyPI first: `python -m twine upload --repository testpypi dist/*`
  - [ ] Verify: `pip install khavis` from a fresh venv works
- [ ] **Docker image built** — `docker build -t kiddhsu/khavis:0.1.0 .`
- [ ] **Docker image pushed** — `docker push kiddhsu/khavis:0.1.0`
- [ ] **Docker image tagged `latest`** — `docker push kiddhsu/khavis:latest`
- [ ] **Docker Hub README** — `docker push kiddhsu/khavis --all-tags` syncs the README

### Documentation

- [ ] **docs/ARCHITECTURE.md** — six-layer architecture explained, with diagrams
- [ ] **docs/PLUGIN_AUTHORING.md** — how to write a plugin in 5 minutes
- [ ] **docs/CONFIG_REFERENCE.md** — exhaustive YAML schema documentation
- [ ] **docs/TROUBLESHOOTING.md** — common errors and fixes
- [ ] **docs/DEPLOYMENT.md** — systemd unit, Docker Compose, k8s manifests
- [ ] **Example scripts in repo** — `examples/01_basic_chat.py` through `examples/10_multi_agent_debate.py`
- [ ] **Link from README to docs** — every doc has a "back to README" link

### Website / landing page (if you have one)

- [ ] **Domain registered** — `khavis.example.com` (placeholder if no real site)
- [ ] **GitHub Pages** site built — `index.md` with tagline, hero code snippet, links to GitHub + docs
- [ ] **Custom 404** in place

---

## T-2 days: prep the announcement content

- [ ] **Show HN post drafted** — `blog/show-hn-post.md`, ≤ 150 lines, technical
- [ ] **HN first-comment drafted** — pre-written technical detail to post as a comment
- [ ] **Launch blog post drafted** — `blog/launch-post.md`, ≤ 1500 lines, with code examples
- [ ] **Dev.to cross-post drafted** — `blog/dev-to-post.md`, tutorial-style
- [ ] **Twitter thread drafted** — `blog/twitter-thread.md`, 12 tweets numbered, each ≤ 280 chars
- [ ] **知乎 / 微信公眾號 post drafted** — `blog/zhihu-post.md`, Traditional Chinese
- [ ] **Code examples assembled** — `blog/code-examples.md`, 10 runnable examples
- [ ] **Email to friends / collaborators** — "I'm launching this Tuesday, would love your honest feedback if you try it"
- [ ] **Reply-bait drafted** — pre-written answers to the most common "why not just use X?" comments

---

## T-1 day: final prep

- [ ] **Tag a release candidate** — `v0.1.0-rc.2` if you made changes this week
- [ ] **Run `khavis doctor` on a fresh machine** — every pool shows `ok` (or `down` with expected reason)
- [ ] **Run the full integration test suite** against real providers
- [ ] **Sanity-check the audit log** — format is valid NDJSON, no PII leaking
- [ ] **Sanity-check `pip install`** — from a brand-new venv, on Python 3.11, 3.12, 3.13
- [ ] **Sanity-check Docker** — `docker run --rm kiddhsu/khavis:0.1.0 khavis --version` returns `0.1.0`
- [ ] **Tag the actual release** — `v0.1.0`
- [ ] **PyPI publish** — `twine upload dist/khavis-0.1.0-py3-none-any.whl`
- [ ] **Docker push** — `docker push kiddhsu/khavis:0.1.0 && docker push kiddhsu/khavis:latest`
- [ ] **GitHub release** — publish the release, copy CHANGELOG excerpt into the description
- [ ] **Set up analytics** — simple counter on the repo (GitHub's own traffic tab), PyPI download stats (`pypistats.org/packages/khavis`)
- [ ] **Set up notifications** — GitHub watch on issues, email alert on PyPI download anomalies
- [ ] **Sleep** — seriously. The launch will go better if you are not exhausted.

---

## Launch day (Tuesday, 9am US Eastern)

The goal of day 0 is **maximum signal, minimum chaos**. Two channels only: HN and Twitter. Save the others for day 1-3.

### 9:00 AM ET — Show HN

- [ ] **Submit Show HN** — title: `Show HN: K.H.A.V.I.S. – One endpoint for 12 LLM providers (BYOK)`
- [ ] **Use the draft** — copy-paste from `blog/show-hn-post.md`
- [ ] **Verify the link** — the GitHub URL works and the README renders
- [ ] **Set a timer** — come back in 30 minutes

### 9:30 AM ET — engage

- [ ] **Post the first-comment with technical detail** — pre-drafted in `blog/show-hn-post.md`
- [ ] **Reply to the first 10 comments within 2 hours** — even if the answer is "good question, I'll think about it"
- [ ] **Acknowledge criticism openly** — "you're right, that is a limitation, here's the workaround" goes much further than defending
- [ ] **Do not shill in unrelated threads** — even if it's your launch day

### 10:00 AM ET — Twitter

- [ ] **Post tweet 1/12** — from `blog/twitter-thread.md`, with the cover image (5 browser tabs, all red)
- [ ] **Reply with tweet 2/12** through tweet 12/12** — each as its own reply in sequence
- [ ] **Pin the thread to your profile**
- [ ] **Set a 2-hour timer** to come back and reply

### Throughout the day

- [ ] **Track HN position** — `https://news.ycombinator.com/` front page position
- [ ] **Reply to every substantive HN comment within 2 hours** — this is the most important engagement metric
- [ ] **Reply to every Twitter reply within 1 hour** for the first 4 hours, 4 hours after that
- [ ] **Watch for the inevitable "why not LiteLLM"** — have the pre-drafted response ready
- [ ] **Do not engage with trolls** — block and move on

### End of day

- [ ] **Count stars** — note the number for the retrospective
- [ ] **Note the top 3 HN comments** — both positive and negative
- [ ] **Note the top 3 HN questions you couldn't answer** — file them as issues tomorrow
- [ ] **Screenshot the HN front-page moment** (if you make it) — for your portfolio

---

## Day 1-3: ripple launches

### Day 1

- [ ] **Reddit r/LocalLLaMA post** — link to launch blog post, focus on "local-first" angle, mention Ollama
- [ ] **Reddit r/MachineLearning post** — same, focus on architecture
- [ ] **Hacker News "Ask HN" follow-up** — `Ask HN: What's your experience routing multiple LLM subscriptions?` (self-promotional angle: "I built this because of X, curious if others have the same")
- [ ] **Dev.to cross-post** — `blog/dev-to-post.md`
- [ ] **Hugging Face** — upload a model card OR a Space demonstrating the router
- [ ] **Product Hunt** — schedule for Day 3 (give it 2 days to gather some upvotes)

### Day 2

- [ ] **Lobsters** — submit `blog/launch-post.md`
- [ ] **Tildes** — submit
- [ ] **Chinese-language channels** — V2EX, 掘金 (juejin), 知乎, 微信公眾號 (use `blog/zhihu-post.md`)
- [ ] **Indie Hackers** — share the journey: "how I built and launched K.H.A.V.I.S. in 6 weekends"
- [ ] **Hacker News comment on related threads** — only if genuinely helpful, never shill

### Day 3

- [ ] **Product Hunt launch** — schedule for 12:01 AM PT (Tuesdays are best)
- [ ] **A "lessons learned" Twitter thread** — quote-tweet your own thread from launch day, share what surprised you
- [ ] **First newsletter mention** — find 3 newsletters (Python Weekly, PyCoder's Weekly, etc.) and submit via their forms

---

## Day 7: first retrospective

By day 7 you should know whether the launch worked or didn't.

- [ ] **Stars** — record the count, compare to expectations
- [ ] **GitHub forks** — record
- [ ] **GitHub issues opened** — categorize: bug / feature / question / docs
- [ ] **PyPI downloads** — `pypistats.org/packages/khavis`
- [ ] **Docker pulls** — Docker Hub dashboard
- [ ] **HN front-page time** — if any
- [ ] **Top 3 issues** — file them, prioritize
- [ ] **Top 3 feature requests** — file them, prioritize, add to roadmap
- [ ] **Top 3 community comments** — reply-thank-you-thread to each
- [ ] **Block list review** — any trolls / spammers to block
- [ ] **Burnout check** — are you still enjoying this?

---

## Ongoing monitoring (weekly)

### Metrics to track

- [ ] **GitHub stars** — trajectory, not absolute count
- [ ] **PyPI weekly downloads** — same
- [ ] **Docker pulls** — same
- [ ] **Issue count** — open vs closed, average response time
- [ ] **PR count** — open vs merged, average review time
- [ ] **Discord/Slack members** (if set up)
- [ ] **NPM-style "used by" count** — check `https://github.com/kiddhsu5/K.H.A.V.I.S./network/dependents`

### Communication cadence

- [ ] **Weekly GitHub digest** — Sunday evening, 5 minutes: what's merged, what's open, any blockers
- [ ] **Monthly "what's next" post** — pinned issue or blog post, what shipped, what's planned
- [ ] **Quarterly retrospective** — what's working, what isn't, when to ask for help

### Community health

- [ ] **Set up Discord OR Slack OR GitHub Discussions** — pick ONE, do not split
- [ ] **Write a CONTRIBUTING.md update** — first-time contributor experience
- [ ] **Tag good first issues** — `good first issue` label, brief description
- [ ] **Tag help-wanted issues** — `help wanted` label, more open-ended
- [ ] **First PR merged by a stranger** — celebrate it publicly
- [ ] **First issue triaged by a stranger** — celebrate it publicly
- [ ] **First docs PR** — almost always typos, always merge and thank

### Sustainability

- [ ] **Set up a GitHub Sponsors** — even if no one sponsors, it's a visible signal
- [ ] **Set up Open Collective** — alternative for transparent finances
- [ ] **Mention sponsorship in README** — one line at the bottom, not on the landing page
- [ ] **Track hours spent** — this matters for the v1.0 SaaS pricing decision
- [ ] **Solo-dev check-in monthly** — am I still having fun? do I need help?

---

## Failure modes to plan for

### "Nobody cares"

- [ ] Day 30 with < 50 stars — that's fine. Most OSS projects take 6-12 months to gain traction.
- [ ] Re-evaluate messaging, not the project. The code is fine; the story might need work.
- [ ] Reach out to 5 people who you think would care, ask them to try it and be honest.

### "Too much interest"

- [ ] Day 1 with 500+ stars and 50+ issues — you will be overwhelmed.
- [ ] Triage ruthlessly. Don't promise anything in issues.
- [ ] Pin a "I am one person" notice in the README if needed.
- [ ] Consider asking for co-maintainers.

### "A security issue is reported"

- [ ] **Respond within 24 hours**, not the typical "I respond within a week" cadence
- [ ] Patch privately first, disclose via GHSA second
- [ ] Update SECURITY.md with the disclosure date

### "A competitor shows up"

- [ ] Don't panic. There is room for multiple routers.
- [ ] Focus on your differentiation (capability-based routing + Ollama-first + 5-min pluggability).
- [ ] Don't trash-talk competitors. It always backfires.

### "Burnout"

- [ ] This is real and common for solo open-source maintainers.
- [ ] Take breaks. The project will survive.
- [ ] If you need to step back, write a "I am on hiatus until X" issue. People will understand.
- [ ] The optional v1.0 SaaS exists in part to fund ongoing maintenance.

---

## What "success" looks like at 90 days

Not these (vanity metrics):

- ❌ 10,000 GitHub stars
- ❌ 1M PyPI downloads
- ❌ 50 newsletter mentions

These (sustainable signals):

- ✅ 100-500 GitHub stars (growing ~5/week)
- ✅ 5-15 real users opening issues
- ✅ 1-3 external PRs merged
- ✅ 1-3 plugins contributed by the community
- ✅ 1-3 docs / README translations contributed
- ✅ You are still excited to work on it
- ✅ You are not burning out

If those are true, the v1.0 SaaS and the long-term sustainability are real possibilities. If not, that's also fine — you shipped something useful, learned a lot, and have a great blog post out of it.

---

## Final note

The most important item on this list is the last one in the "T-1 day" section: **sleep**. Launches are sprints, not marathons. The day after launch, take the day off. Reply to nothing. Touch the keyboard only if there's a real emergency.

The project will be there on Wednesday. So will you.

— kiddhsu5, 2026-09-19 (one day before launch)