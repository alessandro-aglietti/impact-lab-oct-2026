export const meta = {
  name: 'implement-ready-tickets',
  description: 'Implement every ready-for-agent ticket of a feature in parallel worktrees, one PR each, adversarial review + E2E, conflict-resolving merge',
  whenToUse: 'When a .scratch/<feature>/issues/ folder has tickets with Status: ready-for-agent to build end to end. args: {feature, tickets?, autoMerge?, maxReviewRounds?, sessionUrl?}',
  phases: [
    { title: 'Scan', detail: 'read tickets, statuses and Blocked by lines' },
    { title: 'Bootstrap', detail: 'project skeleton + single E2E entrypoint, if missing' },
    { title: 'Implement', detail: 'one worktree + branch + PR per ticket, as soon as its blockers are merged' },
    { title: 'Review', detail: 'three adversarial reviewers per round, posted on the PR' },
    { title: 'Fix', detail: 'verify findings, fix the real ones, re-run E2E' },
    { title: 'Merge', detail: 'serialized: update from main, resolve conflicts, full tests + E2E, merge' },
    { title: 'Integrate', detail: 'fresh clone of main, full E2E of the whole system' },
  ],
}

// ---------- config ----------
const A = args || {}
const FEATURE = A.feature || 'ambrogio'
const ONLY = Array.isArray(A.tickets) ? A.tickets.map(String) : null
const AUTO_MERGE = A.autoMerge !== false
const MAX_ROUNDS = A.maxReviewRounds || 3
const ATTRIB = A.sessionUrl
  ? `End every commit message with the line "Claude-Session: ${A.sessionUrl}" and every PR body with the line "${A.sessionUrl}".`
  : ''
const ISSUES = `.scratch/${FEATURE}/issues`
// Kept OUTSIDE the repo and read-only: agents must never be able to clobber the only copy of the key.
const ENV_FILE = A.envFile || '/Users/gawaine/.config/impact-lab/anthropic.env'
// Existing PRs to pick up instead of re-implementing, e.g. {"00": {"number": 1, "branch": "ticket/00-bootstrap"}}.
const EXISTING_PRS = A.prs || {}

// Shared rules every agent working on code gets.
const GIT_RULES = `
Filesystem and git rules (you run in your own isolated git worktree; other agents work in parallel in other worktrees):
- Never create, modify, move or delete anything outside your worktree, except fresh directories under your scratchpad. ${ENV_FILE} and the main checkout the worktrees hang off are read-only to you.
- Every shell command that changes directory must stop if the cd fails (\`cd X || exit 1\`), and any write or delete after a cd uses an absolute path. A failed cd followed by a relative \`rm .env\` already destroyed the user's API key once.
- Always \`git fetch origin\` first. Never commit to or push main directly. Never force-push anything but your own ticket branch, and only with --force-with-lease.
- To work on an existing PR branch B: \`git switch --detach origin/B\`, commit, then \`git push origin HEAD:B\` (detached avoids "branch already checked out in another worktree").
- Use \`gh\` for every PR operation. You cannot approve your own PR: post reviews with \`gh pr review --comment\` and line comments via \`gh api\`.
${ATTRIB}`

const E2E_RULES = `
End-to-end testing is mandatory, not optional:
- ANTHROPIC_API_KEY lives in ${ENV_FILE} (read-only, outside the repo). Copy it to your worktree before running anything: \`cp ${ENV_FILE} "$(git rev-parse --show-toplevel)/.env"\`. Never edit, move or delete ${ENV_FILE}. Never print, log or commit the key.
- The repo has ONE documented E2E entrypoint (see tests/e2e/README.md, created by the bootstrap step). Every ticket adds its own scenario under tests/e2e/ and the entrypoint runs them all.
- An E2E scenario exercises the deliverable through its real entrypoint (CLI, script, HTTP server, web page via Playwright) on the real versioned data, from a clean state. No mocks of our own code. Where the ticket makes Claude do work at runtime, the E2E calls the real Claude API and asserts on the structured output's shape and invariants, not on exact wording.
- If something needed for E2E is missing (API key, network for a one-off download, a browser), say so explicitly in your result with e2e.passed=false and the reason. Never claim E2E passed without having run it and seen the output.`

// ---------- schemas ----------
const TICKETS_SCHEMA = {
  type: 'object',
  properties: {
    tickets: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'two-digit number, e.g. "04"' },
          path: { type: 'string' },
          title: { type: 'string' },
          status: { type: 'string' },
          blockedBy: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'path', 'title', 'status', 'blockedBy'],
      },
    },
    hasE2EHarness: { type: 'boolean', description: 'origin/main already has tests/e2e/README.md describing a single E2E entrypoint' },
  },
  required: ['tickets', 'hasE2EHarness'],
}

const E2E = {
  type: 'object',
  properties: {
    command: { type: 'string' },
    passed: { type: 'boolean' },
    evidence: { type: 'string', description: 'last relevant lines of real output, or why it could not run' },
  },
  required: ['command', 'passed', 'evidence'],
}

const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    branch: { type: 'string' },
    prNumber: { type: 'integer' },
    prUrl: { type: 'string' },
    summary: { type: 'string' },
    unitTestsPassed: { type: 'boolean' },
    e2e: E2E,
    blocked: { type: 'string', description: 'empty if not blocked; otherwise what a human must provide' },
  },
  required: ['branch', 'prNumber', 'prUrl', 'summary', 'unitTestsPassed', 'e2e', 'blocked'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['blocking', 'minor'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'command run + output, failing input, or exact spec/ADR quote' },
        },
        required: ['severity', 'file', 'claim', 'evidence'],
      },
    },
    e2eRan: { type: 'boolean' },
  },
  required: ['findings', 'e2eRan'],
}

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    fixed: { type: 'array', items: { type: 'string' } },
    rejected: { type: 'array', items: { type: 'string' }, description: 'finding + why it is not real (also replied on the PR)' },
    unitTestsPassed: { type: 'boolean' },
    e2e: E2E,
  },
  required: ['fixed', 'rejected', 'unitTestsPassed', 'e2e'],
}

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    merged: { type: 'boolean' },
    conflictsResolved: { type: 'array', items: { type: 'string' } },
    unitTestsPassed: { type: 'boolean' },
    e2e: E2E,
    mergeSha: { type: 'string' },
    reason: { type: 'string', description: 'why not merged, if not' },
  },
  required: ['merged', 'conflictsResolved', 'unitTestsPassed', 'e2e', 'reason'],
}

const INTEGRATE_SCHEMA = {
  type: 'object',
  properties: { e2e: E2E, failures: { type: 'array', items: { type: 'string' } } },
  required: ['e2e', 'failures'],
}

// ---------- scan ----------
phase('Scan')
const scan = await agent(
  `Read every file in ${ISSUES}/ on origin/main (run \`git fetch origin\` and use \`git show origin/main:<path>\`; fall back to the working tree if the folder is not on origin yet, and say so in the title field).
For each ticket return id (NN prefix), path, title (first heading), status (the "Status:" line value) and blockedBy (ids from the "Blocked by:" line, [] if none).
Also report whether origin/main has tests/e2e/README.md describing a single E2E entrypoint.`,
  { label: 'scan tickets', phase: 'Scan', schema: TICKETS_SCHEMA, effort: 'low', isolation: 'worktree' },
)

const all = scan.tickets
const byId = Object.fromEntries(all.map(t => [t.id, t]))
const DONE = new Set(all.filter(t => /^(done|resolved)$/i.test(t.status.trim())).map(t => t.id))
const ready = all.filter(t => t.status.trim() === 'ready-for-agent' && (!ONLY || ONLY.includes(t.id)))
const inRun = new Set(ready.map(t => t.id))

// A ticket is runnable only if every blocker is already done or is itself in this run.
const runnable = []
for (const t of ready) {
  const missing = t.blockedBy.filter(b => !DONE.has(b) && !inRun.has(b))
  if (missing.length) log(`skip ${t.id}: blocked by ${missing.join(', ')} which is neither done nor ready in this run`)
  else runnable.push(t)
}
log(`${runnable.length} ticket(s) to implement: ${runnable.map(t => t.id).join(', ') || 'none'}`)
if (!runnable.length) return { implemented: [], skipped: ready.map(t => t.id) }

// ---------- merge lock: merges are serialized so each one updates from the latest main ----------
let mergeChain = Promise.resolve()
function withMergeLock(fn) {
  const p = mergeChain.then(fn)
  mergeChain = p.catch(() => {})
  return p
}

// ---------- one ticket: implement -> (review -> fix)* -> merge ----------
async function deliver(t, implementPrompt) {
  const tag = t.id
  phase('Implement')
  const existing = EXISTING_PRS[tag]
  if (existing) log(`${tag}: picking up existing PR #${existing.number} (${existing.branch})`)
  const impl = existing
    ? { branch: existing.branch, prNumber: existing.number, prUrl: `PR #${existing.number}`, e2e: null, blocked: '' }
    : await agent(implementPrompt, {
      label: `implement ${tag}`, phase: 'Implement', schema: IMPL_SCHEMA, isolation: 'worktree',
    })
  if (!impl) return { id: tag, merged: false, reason: 'implementer died or was skipped' }
  if (impl.blocked) {
    log(`${tag} blocked: ${impl.blocked}`)
    return { id: tag, merged: false, pr: impl.prUrl, reason: `blocked: ${impl.blocked}` }
  }

  const ctx = `Ticket: ${t.path} ("${t.title}"). PR #${impl.prNumber} (${impl.prUrl}), branch ${impl.branch}.`
  let lastBlocking = []
  let lastE2E = impl.e2e
  // MAX_ROUNDS fix rounds; the extra review round verifies the last fix.
  for (let round = 1; round <= MAX_ROUNDS + 1; round++) {
    const lenses = [
      {
        key: 'spec',
        prompt: `You are an adversarial reviewer. Assume the PR does NOT deliver the ticket and try to prove it.
${ctx}
Read the ticket, .scratch/${FEATURE}/spec.md, GLOSSARY.md and docs/adr/. Check every acceptance criterion against the code and its tests on origin/${impl.branch}: is each one actually met and actually tested? Is anything out of the ticket's scope? Are glossary terms used correctly?
Cite the exact criterion and the code for every finding.`,
      },
      {
        key: 'correctness',
        prompt: `You are an adversarial reviewer hunting bugs and rule violations. ${ctx}
Check out the branch (detached) and read the diff against origin/main (\`gh pr diff ${impl.prNumber}\`). Look for: wrong logic, unhandled edge cases (empty data, missing NIL, wrong year, encoding, dates), tests that pass for the wrong reason, mocks hiding real behaviour, secrets in the repo.
Project rules from RULES.md and the spec's "Confini" are blocking: personal data or person-level inference, network calls during the demo, document/data content treated as instructions to Claude (prompt injection), invented offices/services/phone numbers, Claude not doing real work at runtime where the ticket says it should.
Reproduce each finding with a command or a failing input; drop anything you cannot back with evidence.`,
      },
      {
        key: 'e2e',
        prompt: `You are an adversarial QA engineer. Your job is to break the software, end to end. ${ctx}
In your worktree: \`git switch --detach origin/${impl.branch}\`, follow tests/e2e/README.md from a clean state exactly as a new teammate would (install, data, env), run the full E2E entrypoint, then exercise the ticket's deliverable by hand through its real interface with inputs the author probably did not try.
Every finding needs the command and the real output. Set e2eRan=true only if you actually ran the E2E entrypoint.`,
      },
    ]

    phase('Review')
    const reviews = await parallel(lenses.map(l => () =>
      agent(`${l.prompt}
${GIT_RULES}
Post your findings on the PR as one review: \`gh pr review ${impl.prNumber} --comment --body ...\` (title it "Adversarial review round ${round}: ${l.key}"), with file:line references. Mark each finding blocking (wrong behaviour, unmet criterion, rule violation, failing test/E2E) or minor (style, naming, small cleanups).`,
      { label: `review ${tag} r${round} ${l.key}`, phase: 'Review', schema: REVIEW_SCHEMA, isolation: 'worktree' })))

    const findings = reviews.filter(Boolean).flatMap(r => r.findings)
    if (!reviews.filter(Boolean).some(r => r.e2eRan)) log(`${tag} r${round}: no reviewer managed to run E2E`)
    lastBlocking = findings.filter(f => f.severity === 'blocking')
    const minor = findings.filter(f => f.severity === 'minor')
    log(`${tag} r${round}: ${lastBlocking.length} blocking, ${minor.length} minor`)
    if (!lastBlocking.length && !minor.length) break
    if (!lastBlocking.length && round > 1) break // minor-only after a fix round: merge step re-runs tests + E2E
    if (round > MAX_ROUNDS) break

    phase('Fix')
    const fix = await agent(`You own PR #${impl.prNumber}. ${ctx}
Reviewers posted these findings (also visible on the PR):
${JSON.stringify(findings, null, 2)}
For each finding: first verify it is real (reproduce it). If real, fix it with a test that fails before the fix. If not real, reply on the PR explaining why with evidence. Fix all real blocking findings; fix minor ones when cheap.
Then run the full unit test suite and the full E2E entrypoint, push to ${impl.branch}, and comment on the PR with what changed and the E2E output.
${GIT_RULES}
${E2E_RULES}`,
      { label: `fix ${tag} r${round}`, phase: 'Fix', schema: FIX_SCHEMA, isolation: 'worktree' })
    if (!fix) return { id: tag, merged: false, pr: impl.prUrl, reason: 'fixer died' }
    lastE2E = fix.e2e
    if (!lastBlocking.length) break // only minor findings, now fixed
  }

  if (lastBlocking.length) {
    log(`${tag}: still ${lastBlocking.length} blocking finding(s) after ${MAX_ROUNDS} rounds, not merging`)
    return { id: tag, merged: false, pr: impl.prUrl, reason: 'unresolved blocking findings', findings: lastBlocking }
  }
  if (!AUTO_MERGE) return { id: tag, merged: false, pr: impl.prUrl, reason: 'autoMerge=false: ready for human merge', e2e: lastE2E }

  const merge = await withMergeLock(() => {
    phase('Merge')
    return agent(`You are merging PR #${impl.prNumber}. ${ctx}
1. \`git switch --detach origin/${impl.branch}\`, then \`git merge origin/main\`. Resolve every conflict by keeping the intent of BOTH sides: read the other ticket's PR/ticket file to understand what it needed (shared files like the E2E entrypoint, dependency manifests, data manifests usually need a union, not a pick). Record each resolved conflict.
2. Update the ticket file ${t.path}: set "Status: done" and append under "## Comments" a line with the PR link and a one-line summary.
3. Run the full unit test suite and the full E2E entrypoint on the merged result. If anything fails, fix it (it's usually an interaction with what main gained since the branch was cut).
4. Push to ${impl.branch}. Wait for any GitHub checks (\`gh pr checks ${impl.prNumber} --watch\`, skip if there are none).
5. Only if unit tests AND E2E passed: \`gh pr merge ${impl.prNumber} --squash --delete-branch\` and report the merge commit SHA. Otherwise do not merge; comment on the PR why.
${GIT_RULES}
${E2E_RULES}`,
      { label: `merge ${tag}`, phase: 'Merge', schema: MERGE_SCHEMA, isolation: 'worktree' })
  })
  if (!merge) return { id: tag, merged: false, pr: impl.prUrl, reason: 'merger died' }
  log(`${tag}: ${merge.merged ? 'merged ' + (merge.mergeSha || '') : 'NOT merged: ' + merge.reason}`)
  return { id: tag, merged: merge.merged, pr: impl.prUrl, reason: merge.reason, conflicts: merge.conflictsResolved, e2e: merge.e2e }
}

// ---------- bootstrap: one E2E entrypoint before parallel tickets start ----------
let bootstrap = Promise.resolve({ merged: true })
if (!scan.hasE2EHarness) {
  phase('Bootstrap')
  bootstrap = deliver({ id: '00', path: '(bootstrap)', title: 'project skeleton and E2E harness' },
    `Create the project skeleton every ticket of ${ISSUES}/ will build on, so parallel tickets don't each invent their own.
Read ${ISSUES}/*.md, .scratch/${FEATURE}/spec.md, docs/adr/ and starter/ (runs_on_claude.py, portal.py, CLAUDE.md). Stay consistent with starter/ (Python) unless the tickets clearly need otherwise.
Deliver, on branch ticket/00-bootstrap based on origin/main:
- dependency manifest + lockfile, package layout, unit test runner, a single command to run all unit tests;
- tests/e2e/ with ONE entrypoint that runs every scenario in the folder (each ticket will add one), a trivial smoke scenario proving the harness itself works, and tests/e2e/README.md describing setup from a clean clone, required env vars (ANTHROPIC_API_KEY), and how to add a scenario;
- Playwright set up for the web UI ticket if one exists;
- no ticket functionality.
Run unit tests and E2E, commit, push, open a PR titled "Bootstrap: project skeleton and E2E harness" with the commands and their output in the body.
${GIT_RULES}
${E2E_RULES}`)
}

// ---------- tickets: each starts as soon as its in-run blockers are merged ----------
const results = {}
function run(t) {
  if (results[t.id]) return results[t.id]
  results[t.id] = (async () => {
    const boot = await bootstrap
    if (!boot.merged) return { id: t.id, merged: false, reason: 'bootstrap not merged' }
    const deps = await Promise.all(t.blockedBy.filter(b => inRun.has(b) && byId[b] !== t).map(b => run(byId[b])))
    const failed = deps.filter(d => !d.merged).map(d => d.id)
    if (failed.length) {
      log(`skip ${t.id}: blocker(s) ${failed.join(', ')} not merged`)
      return { id: t.id, merged: false, reason: `blocker(s) ${failed.join(', ')} not merged` }
    }
    return deliver(t, `Implement ticket ${t.path} ("${t.title}").
Read the ticket, .scratch/${FEATURE}/spec.md, GLOSSARY.md, docs/adr/ and the code already on origin/main (the ticket's blockers are merged there).
1. Branch ticket/${t.id}-<slug> from origin/main.
2. Implement with /tdd at the seams the ticket implies. Keep scope to the ticket; anything else goes in the PR body as a follow-up.
3. Add the ticket's E2E scenario under tests/e2e/ that proves every acceptance criterion through the real entrypoint.
4. Run the full unit test suite and the full E2E entrypoint; iterate until both pass.
5. Commit, push, open a PR titled "${t.id}: ${t.title}" whose body lists each acceptance criterion with where it is implemented and tested, and pastes the E2E output.
If the ticket needs something only a human can provide (credentials, a manual download, a product decision not in the spec/ADRs), still open the PR with what you could do and fill "blocked".
${GIT_RULES}
${E2E_RULES}`)
  })()
  return results[t.id]
}

const outcomes = await Promise.all(runnable.map(run))
const bootOutcome = scan.hasE2EHarness ? null : await bootstrap

// ---------- integration E2E on main ----------
let integration = null
if (outcomes.some(o => o.merged)) {
  phase('Integrate')
  integration = await agent(`Every ticket PR from this run has been merged to main. In your worktree: \`git fetch origin && git switch --detach origin/main\`, wipe any untracked build/data artifacts (\`git clean -xfd\`), set up from scratch following tests/e2e/README.md exactly, and run the full E2E entrypoint. Then walk the spec's demo (.scratch/${FEATURE}/spec.md, section "Demo") as far as the merged tickets allow, through the real interfaces. Report real output; list every failure with the command that shows it. Do not fix anything.
${E2E_RULES}`,
    { label: 'integration e2e', phase: 'Integrate', schema: INTEGRATE_SCHEMA, isolation: 'worktree' })
}

return { bootstrap: bootOutcome, tickets: outcomes, integration }
