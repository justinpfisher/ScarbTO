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

The zero-model `verbatim` exception is narrowly restricted to an exact whole
City-source field value, stored as a single `VERBATIM` lock with matching
source-fact digest and an explicitly allowlisted official source. Marking
ordinary Scarb-authored prose as `verbatim` now fails qualification. This is
not a new general-purpose bypass for copy from a new feed or public web page.


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

Run `python scripts/scarb_ai_voice.py verify --requests STATE/requests.json
--config STATE/config.json --state STATE --output CANDIDATE` in the protected
GMKtec authoring environment after compilation and before publishing the
candidate. It compares the entire candidate against independently retained,
validated accepted receipts; changing displayed copy after AI acceptance fails.
It is not a cryptographic signature or a substitute for code review, and the
publisher cannot infer validity from a `receipt_sha256` field supplied by an
untrusted catalogue alone.

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


## Owner-authorized bounded existing-paid pilot (offline implementation)

The owner subsequently authorized existing paid API funds for Scarb within a
temporary C$20/month ceiling. This does not authorize a purchase, top-up, new
payment method, automatic recharge, postpaid exposure or credential changes.
The original promotional path above remains unchanged. The separate
`existing_paid_api_credits` variant requires verified existing organization and
Scarb project identity, a current sufficient balance receipt, and verified
`auto_recharge_disabled` and `postpaid_disabled` attestations. Setting those
fields is not itself verification of provider billing settings.

The bounded implementation retains the existing US$5 monthly application fuse
and adds a cumulative, non-monthly US$0.25 initial pilot ceiling. It permits only
GPT-6 Luna as author and GPT-6.1 Terra as the independent reviewer. Both calls
are reserved under the same exclusive private-state lock before transmission.
An uncertain or failed attempt retains its reservation and held-attempt marker;
it is not automatically retried. Accepted unchanged cache entries require no
new calls. A reported token overrun closes both fuses. These application controls
are not provider-enforced billing controls and do not cover unrelated callers.

This variant has synthetic positive and negative tests only. No live activation,
API call, account/billing modification or credential discovery is implied.
Real qualification still requires the verified project/key custody and funding
receipt plus the bounded pilot execution coordinated by the existing owner.


### Bounded prepaid pilot when provider cutoff is not guaranteed

A separately reviewed offline variant records `billing_mode` as
`prepaid_cutoff_not_guaranteed`; it must not claim `postpaid_disabled`. It is
restricted to the two exact approved public packet hashes and the dedicated
Scarb project. It requires a balance receipt no older than one hour, at least
US$5.25 prepaid balance (US$5 buffer plus the whole US$0.25 pilot), and verified
automatic recharge off. The same held-attempt, cumulative pilot and monthly
fuses apply. This is not authorization for ongoing paid automation. Provider
cutoff may lag and unrelated account usage is outside the application fuse;
these facts must remain explicit in the execution decision. No real funding
receipt or API activation is created by this implementation.


## Offline fact-slot contract v2 (not activated)

`scripts/scarb_ai_fact_slots.py` is an offline-only, separately versioned authoring
contract. It has no live transport, credential loader or generation CLI. The
explicit `generate_fixture` simulator uses only canned responses and disposable
fixture state, marked `test-fixture`. V1 prompts, schema,
cache keys, historical receipts and held attempts remain unchanged. No v2 receipt
is accepted by the publisher or installed by this prototype.

A strict per-packet schema requires every protected name as an object key. The
writer chooses each slot's unique integer rank and preceding connective prose,
plus a final prose tail and the unchanged evidence IDs. The assembler inserts the
original protected token after each preceding fragment. This removes token
spelling/copying from prose output without fixing sentence order or supplying a
creative template. Required keys, unknown keys, duplicate/out-of-range ranks,
model-supplied tokens, new number/URL/markup markers, evidence IDs and expanded
length remain fail-closed. Existing whitespace-lock rules still apply.

The separate reviewer receives the original packet, FULL reconstructed tokenized
paragraph and materialised final text. Meaning, omissions, relationship/order,
source prominence, safety and 2x voice must all pass; valid structural output alone
is not semantic or stylistic qualification. Source values are unchanged. The
original whole-official-value verbatim lane is not broadened.

V2 version, exact prompts, per-packet schema and models bind its distinct cache
identity. The fixture helper always labels output `test-fixture`; it is not a
production receipt. Future dispatch integration must separately bind raw slot
output, deterministic assembly and independent review in the receipt; preserve the
same cumulative reservations and first-attempt holds; and prohibit interpreting a
new schema as permission to retry a held packet. It must reserve the new schema,
full reconstructed reviewer input and output caps before any call. Existing v1
cost estimates are NOT a qualified v2 budget. No model calls are enabled here.

Prospective qualification cases are distinct synthetic public-source contracts:
a source-note with two exact facts plus one safety caveat; a no-fact functional
control; and an accessibility phrase with required leading/trailing whitespace.
They are not either previously held packet or a renamed replay. Live use requires
separate exact-case funding/scope approval, schema review and actual writer/reviewer
plus accepted-output rendering. These offline fixtures claim none of that.


Offline v2 handoff simulation now reserves both calls before exchanging canned
responses, checks explicit funding/config/schema envelopes, uses a separate
versioned fixture receipt directory and refuses an existing exact v1 or v2 hold.
It revalidates raw slots, reconstructed writer, final text, evidence, reviewer and
receipt digest on cache reuse. No real environment/key is read. Its synthetic
funding identity is provided solely to exercise the existing checks. No production
receipt is minted. Fixture reservations remain conservatively charged in the
throwaway ledger even after success. Tests separately exercise valid-draft /
oversized-candidate word and character limits, empty-lock controls, and mandatory
boundary whitespace. The live transport/production receipt route remains absent.


### Disabled production handoff implementation (supersedes prototype absence above)

V2 now exposes `generate(..., enable_v2=False, approved_packet_sha256=(), env=None)`.
There is no CLI/default activation: exact packet approval, explicit protected env,
existing config funding checks and its private paid packet whitelist all remain
required. It calls only the existing bounded v1 HTTP implementation, never a new
endpoint. Both calls are conservatively reserved in the SAME ledger/exclusive lock;
failures retain the reservation and hold, and an original exact v1 hold prevents
this version becoming a replay route. Success also retains the conservative
reservation (rather than refunding it). Reported usage overrun exhausts the existing
fuses. No private state or approval whitelist was changed during implementation.

Immutable accepted-v2 receipts bind packet hash, exact version/prompts/schema/models,
raw slot output, reconstructed writer, final text, independent verdict and measured
usage. `compile_catalogue` verifies all of these and rejects fixture origins; its
public result uses the unchanged existing reader schema. The private staging,
comparison and byte-attestation bridge accepts explicit `authoring_version="v2"`
(default v1) and revalidates private v2 receipts before deriving JSON/MJS. This is
not permission to install or publish a catalogue. Mocked production-route tests
use temporary state and patched transport only, never real credentials or requests.
Provider schema acceptance and a real accepted writer/reviewer result remain unproven.


The next v2 qualification eligibility is separately fixed in source to packet
`d17d1dc701dfaf10f04144afab0b7f2cfe2c61d549a2e9036220a9a20c10de1a`.
V1 funding validation and its original two-packet list are unchanged; v2 uses that
same funding receipt for truthful prepaid identity/freshness/no-reload checks,
while its own exact eligibility replaces the v1 packet-selection rule only in the
v2 entry point. Both original held packet hashes and all other packets are refused
in this bounded prepaid variant. The explicit live-default-off and approval gates
still apply. No funding configuration has been rewritten or new call authorised by
this code. The prospective two-call reserve is US$0.088814, combined US$0.154281
with existing held US$0.065467; a later funded invocation needs exact hashes and
fresh provider receipt verification. Finite journals preserve request/validation
stages, response presence and measured token counts only, not raw response text.


After the once-only v2 qualification was independently rejected, all three actual
packet digests are sealed in the v2 dispatch entry point before cache lookup,
funding, reservation or transport. These content-addressed refusals survive prompt,
schema and version changes. The prior v2 eligible digest is now also refused; no
new packet has been authorised. V1 historical implementation remains unchanged:
its own hold key includes prompts/schema, so the stable digest seal described here
is a V2 entry-point guarantee, not a claim of retrofitting v1. No earlier journal
or ledger was changed. Future v2 reviewer failures preserve only schema-valid flag,
approve/meaning/limitations/voice booleans and an issues-present boolean, never
free-form issue text. Existing held results are not retroactively interpreted.
