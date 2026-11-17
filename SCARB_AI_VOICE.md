# Scarb Voice Gateway — AI-first authoring

Owner revision: November 17, 2026. This supersedes **template-first creative
writing**, not the 2x personality, factual safeguards or Dot's sole release role.
The existing catalogue becomes a store of accepted writing, not a ceiling on what
Scarb can say. No live model call, credential/billing change or deployment is
claimed by this candidate.

## What changes

New editorial copy is written by an AI from a narrowly qualified public input,
then checked by deterministic guards and a separate model review. The writer can
vary phrasing and rhythm and notice what is genuinely interesting in the provided
facts. It cannot invent facts to sound enthusiastic. Buttons and access/safety
language stay direct; official values and required wording can pass through
unchanged. An AI can author a useful button once; it need not reinvent the button
for every visitor.

The browser stays static and has no API key. The existing trusted GMKtec authoring
slot produces an accepted catalogue. Existing JS/Python generators consume that
catalogue. This is not a new service, server, database, public inference endpoint,
ChatGPT browser bot or separate release.

## Implemented interfaces

| File | Responsibility |
|---|---|
| `scripts/scarb_ai_voice.py` | Standard-library Responses API writer, separate model review, protected-value checks, receipts/cache, local budget reservations, held attempts, plan/generate/compile CLI |
| `scripts/collect_scarb_ai_requests.mjs` | Build requests from current SCARB_COPY plus optional hash-qualified public DineSafe release; only allowlisted event fields; no browser settings or private publisher text |
| `docs/scarb-ai-copy.mjs` | Pure accepted-output resolver, taking an independently constructed current request-hash manifest; rejects missing/stale/unclassified/test-origin copy |
| `config/scarb-ai.example.json` | Disabled example; zero API-value allowance, no credential or assumed funding grant |
| `tests/test_scarb_ai_voice.py`, `tests/scarb-ai-copy.test.mjs` | Offline fixture tests; not evidence of successful API access, writing quality, GMKtec or live publication |

`generate(packet, config, state)` accepts a classified public packet. Its fields
are `id`, `surface`, `kind`, `draft`, `locks`, `evidence`, `limits`. Every source
reference has `id`, `source`, `sha256` and a bounded `fact`. Production callers must
obtain the facts and hashes from the existing qualified-source pipeline. A valid
hash shape is not source qualification.

The collector's catalogue classification table covers the existing named entries;
Dot extends it as the remaining copy producers migrate. The API accepts all of the
named site/output families, but that does not itself prove those producers are
connected. Unknown catalogue keys fail until classified. `eventRequests()` offers
reusable per-event output for map/list, future briefs/RSS, Community Publishing
and embeds. It excludes addresses, coordinates and non-allowlisted fields.

### Protected text and genuine creativity

Values appear as `{{LOCK:NAME}}`, `{{LOCK:OUTCOME}}`, `{{LOCK:INSPECTION_DATE}}`,
`{{LOCK:OBSERVED_DATE}}`, or other named locks. The model must retain each once.
The guard restores their original values after writing and counts the final text.
It rejects missing/repeated locks, new digits/URLs/markup, missing evidence IDs,
extra fields and length overruns. The model is free to write the connecting prose.
The separate reviewer checks meaning, limitations and recognisable Scarb voice;
a schema-compliant but generic or unsupported paragraph is not accepted.

This does **not** mathematically prove semantic equivalence. A model can invent a
claim without digits or change what a sentence implies while retaining tokens.
The independent model check reduces that risk but is not infallible. Keep normal
independent software/release review, a one-time real model/voice qualification,
source tests and rendered-output acceptance. Do not turn that into daily human
content curation or label offline mock responses as model evidence.

## Model and usage policy

Initial pilot: `gpt-6.1-terra` author and `gpt-6.1-sol` reviewer, low reasoning,
Standard service tier, at most 2,000 output tokens per call (including reasoning),
no tools, `store:false`, no background response. These are supported candidates,
not winners of a live Scarb writing evaluation. `gpt-6-luna` is available for a
bounded comparison; never switch to a more expensive model silently.

A newly accepted editorial unit normally uses **two API calls**. Unchanged inputs
use **zero**. Verbatim protected content uses zero. Rejecting a draft does not
trigger creative retries in a loop. A held-attempt marker prevents the same input
from being retried automatically after a crash, refusal or outage. An operator
may clear that one marker only after resolving the cause and verifying no active
run; that is operational recovery, not regular editorial curation.

Caching includes the exact request, prompts, schema, code version and model IDs.
Changing a source fact, voice prompt or model invalidates that entry. Daily fetch
times are not part of per-event identities, so unchanged history is not rewritten
just to sound new. Generated-at time is not a source-inspection, collection or
publication date. Existing archived editions and finalised receipts are never
retranslated. A new composition gets its own version/evidence receipt.

At rates verified November 17, 2026, Terra is US$1 input/US$5 output per million
tokens; Sol is US$2/US$10; Luna is US$0.10/US$0.50. These are estimates for short
Standard requests, not an account quote. Reasoning, reviewer input/output and
failed attempts count too. The adapter records actual reported token quantities,
estimates undiscounted text cost and reserves a conservative bound before both
calls. No external pricing feed or chargeable tool is used. Recheck rates before
activating or changing models. Account/provider controls are still necessary:
local estimates cannot prove that an account will not charge cash.

## Funding and credentials: disabled until verified

ChatGPT messages/Work allowances are not API credentials. Eligible Pro accounts
may claim an API credit benefit in a linked API organisation, but eligibility,
actual grant, expiry and the project to be billed must be verified for this owner.
A grant can consume purchased credits after promotion expiry/exhaustion if those
are available. Do not assume an account cannot incur cash charges merely because
it had promotional credits. No payment method, Auto Recharge, bought credits,
new credential or widened access is authorised by this implementation.

Copy the example to **protected GMKtec state outside the repository and public
docs**, using the existing approved custody process. Activation requires:

- Existing authorised `OPENAI_API_KEY`, `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID` in the
  protected process environment, never committed or pasted into chat.
- A verified funding receipt in that private config: `kind` is
  `promotional_api_credits`; exact `organization` and `project`; zoned
  `verified_at` and `expires_at`; `remaining_usd`; `cash_fallback_disabled:true`.
- `enabled:true`, a positive `month_cap_usd` no higher than US$5 **of verified
  allocated credits**, and `SCARB_AI_ENABLE=1`. The example remains false/zero.
  This is not permission for US$5 in cash spending; the project still targets C$0.
- Applicable existing provider spend controls and no unapproved purchased-credit
  or recharge fallback. The local boolean records verified controls; it does not
  change or enforce the API billing account. Provider hard limits can lag.

Funding evidence must still be within its real expiry and cannot be future-dated.
The adapter accepts a verified current billing-cycle receipt up to 35 days old;
it does not invent renewal evidence or require daily manual curation. A missing
renewal/grant or protected credential holds generation. Do not search unrelated
workspaces for secrets or create broader access as a workaround.

## Command path (GMKtec, once prerequisites exist)

Use actual authorised local paths, represented below by STATE and RELEASE.
Never store funding receipts, API keys, raw responses or ledgers in `docs/`.

```text
node scripts/collect_scarb_ai_requests.mjs --output STATE/requests.json
# Optional qualified events: add --release RELEASE --release-sha256 VERIFIED_BYTE_SHA256
python scripts/scarb_ai_voice.py plan --requests STATE/requests.json --config STATE/config.json --state STATE
python scripts/scarb_ai_voice.py generate --requests STATE/requests.json --config STATE/config.json --state STATE
python scripts/scarb_ai_voice.py compile --requests STATE/requests.json --config STATE/config.json --state STATE --output STATE/catalogue-candidate.json
```

`plan` never calls a model. `generate` produces immutable accepted receipts or
holds the new input. `compile` needs an accepted entry for **every exact request**,
rejects test-origin receipts, and refuses to overwrite an existing destination.
Use a fresh candidate name on subsequent runs; retain prior files for rollback.
A failed unit does not cause a partial catalogue to replace the previous one.

## Dot integration into the existing work, not a competing rewrite

Dot has already begun universal producer wiring. Preserve that work and integrate
this additive layer rather than restarting it or overwriting shared files.

1. Keep the current gateway call sites. For current-copy creation, supply the
   accepted catalogue plus an **independently built request manifest** to the
   resolver. `createScarbAiResolver(catalogue, {requestId: packetSHA256})` returns
   a lookup that throws on a missing entry. Python uses `compile_catalogue()` or
   its accepted JSON. Never derive expected hashes from the output being checked.
2. Make accepted AI copy the canonical source for the migrated static catalogue,
   then regenerate marked HTML, neighbourhood pages and non-archived directories.
   Adapt the existing exact-copy checker to compare with this accepted canonical
   result. Do not merely append AI prose after the existing gate or keep two
   conflicting copy catalogues. The current 15-string checker is not universal.
3. Reuse event text by event identity and exact factual packet hash. Client-side
   Community Publishing can select/deduplicate/order those accepted event blocks
   and assemble its factual heading/coverage/date/notice from qualified functional
   copy. Word/character caps and physical PDF fit are checked **after** assembly.
   A publisher's arbitrary area combination does not require a browser API call.
   Bespoke free-form whole-edition AI synthesis on demand is not added here.
4. Pass every remaining house-copy producer through the same accepted-output
   mechanism: map/list/filter/saved area, findings/source notes, errors, metadata,
   alt/ARIA, future weekly and RSS generators, editor/evidence/export/embed. Keep
   official facts, mandatory legal/source wording and sealed history in their
   explicit preservation lanes. A new literal inserted outside those lanes must
   fail the existing release coverage check. This contribution alone does not
   establish that every producer is migrated.
5. Preserve archival renderer versions and allocate a new future-only weekly
   composition revision. Do not rebuild dated HTML, change RSS GUIDs/dates,
   source checked/observed times, boundary registry IDs or finalised receipts.
   Keep the evidence-linked original text available beneath any explanation.
6. Keep City freshness independent of AI availability. Consume a release only
   after existing source qualification; do not add API calls to the hosted public
   refresh job. Source updates can retain approved functional text and source
   records while new editorial copy is held. Do not show an old area's editorial
   passage as though it explained a changed input. Use a previously qualified
   honest unavailability notice, or retain the whole dated prior edition.
7. Run in the existing authorised trusted GMKtec slot, not a public-PR runner or
   paid hosted fallback. Integrate checks in the existing workflow after Dot
   reconciles shared files. Nothing in this contribution dispatches a job or
   installs a new service/schedule. The cadence should follow material input
   changes, not page loads or arbitrary rewording for freshness.

## Qualification and completion

Offline tests executed in the isolated Chat tooling workspace: Python contract,
transport fixtures, funding/budget/cache/failure tests and Node collector/resolver
tests. These are **not** GMKtec qualification, live model tests, browser/PDF checks,
an independent review or deployed/live proof.

Before release, Dot must verify authorised funding/access; exercise actual API
responses on representative real/public inputs (boundary explanation, positive
inspection, conditional/closed result, no-update period, stale source, compact UI
and a print panel); evaluate source fidelity and 2x voice; complete producer wiring;
rerun exact-head Node/Python, fixture regeneration, rendered desktop/mobile/zoom,
PDF/PNG/receipt recovery and independent release review. Include negative tests
for an unregistered new string, altered output, missing receipt, rejected review,
429/timeout, grant expiry and the unchanged-record/zero-call case. Preserve the
last-good release throughout. Record planned, implemented, tested, API-qualified,
merged, deployed and verified-live separately in CURRENT_STATE.md.

The style decision is approved. No extra routine owner approval is needed.
Account funding/credentials, mandatory platform confirmations or a new cash
charge are genuine protected prerequisites, not permission to weaken checks.

## Official references checked November 17, 2026

- API credit benefit and activation/expiry: https://help.openai.com/en/articles/20001626-api-credits-benefit-for-eligible-chatgpt-subscriptions
- Separate billing: https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform
- Responses structured outputs and refusal handling: https://developers.openai.com/api/docs/guides/structured-outputs
- Models/pricing: https://developers.openai.com/api/docs/models and https://developers.openai.com/api/docs/pricing
- Spend controls: https://developers.openai.com/api/docs/guides/spend-limits
- Data controls: https://developers.openai.com/api/docs/guides/your-data

`store:false` is not a promise of zero provider retention; abuse-monitoring/data
controls still apply. Only qualified **public** data is sent by the supplied
collector. Private publisher settings and family/account material are excluded.
