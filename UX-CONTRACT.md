# ourcommunity interaction contract

Scope: local first product authorized by the user's 2026-10-29 request to continue development. Product research remains unvalidated. Korean `ko-KR`, `Asia/Seoul`; synthetic demo accounts and local credentials only. No external identity, push provider, live users or deployment is implied.

## Business context and sources

| Policy | Source | UI consequence |
|---|---|---|
| Private groups and current membership checks | docs/product-specs/ourcommunity/prd-draft.md; community backend contract | No private payload before login/membership; 401 re-auth and 403 access screen clear group caches |
| Durable messages and idempotent attendance/RSVP | docs/product-specs/ourcommunity/data-architecture.md | Server-confirmed success; same request key on retry; poll/backfill current data |
| Collective nonmonetary assets, no message rewards | docs/product-specs/ourcommunity/shared-growth.md | Growth from verified participation, no personal rank/decay; corrections remain auditable |
| Coarse optional activity, small-group protection | docs/product-specs/ourcommunity/activity-patterns.md | Public default off; personal consent separate; no exact people/message/online numbers |
| Local-only implementation and conservative privacy assumptions | docs/implementation/local-product.md | Demo visibly labeled; no real personal data; production policies remain unresolved |
| Isolated preview deployment variant | docs/implementation/preview-deployment.md; preview API metadata | Synthetic roles only; credential entry and external sharing unavailable; first-visit one-hour expiry or restart resets data |
| Billing/legal commitments | Not part of this implementation | No purchase, terms acceptance, external messages or third-party sign-in buttons |

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | Native select via shared Field styling | DESIGN.md | native OS popup accepted | keyboard/browser tests |
| Date | Native datetime-local with explicit KST parsing | DESIGN.md; format.ts | native OS locale accepted | timezone and browser create tests |
| Form | Field + Button + app validation | web/src/components/ui.tsx | create/login/inline | error association, duplicate, cancel tests |
| Scrollbar | Global web/src/styles.css | DESIGN.md tokens | document/chat-log | computed style, mobile scrolling |
| Toast | Shared ToastProvider | web/src/components/ui.tsx | success/info/error | status live region |
| CRUD | React Router + API wrapper, shared mutation semantics | server invariants; this contract | create returns list, inline state refresh | full browser workflow + backend tests |

No data table bulk selection is implemented; table-selection ownership is not applicable. No upload control is implemented. No existing UI primitive/sibling flow existed before this change. Event creation and announcement creation establish the shared form behavior; event cancellation, message removal and membership removal share confirmation behavior.

## Flow ledger

| Operation | Pending and result | Failure and navigation |
|---|---|---|
| Login/register/demo login | Disable duplicate; fetch session/CSRF; return to safe internal original path | Generic credentials error, preserve username, no password URL/storage |
| Preview role selection | Existing demo controls; keep the visitor space when switching roles | Unknown session mode shows only error/retry, never credential inputs; expired space requires a new session |
| Send message | Show sending; keep stable client ID until ACK; clear draft only after confirmed | Keep draft and retry same ID; no unsafe autoqueue/persistent local chat storage |
| Create event/announcement | Submit disabled; server result then close/return list and toast | Preserve input; fields/summary; cancel/back uses shared discard confirmation |
| RSVP/cancel/accept offer | Pessimistic server confirmation; refetch detail/count | Never infer a seat from cache. Reuse operation ID on uncertain retry; stale state explained |
| Confirm/correct attendance | Staff only; self-confirm disallowed | Reflect server permission/correction errors; no optimistic asset award |
| Public/consent/role changes | Explicit confirmation when widening or removing access | Keep previous state until server confirmation; scoped error and retry |
| Leave/delete/report | Object/consequence in app dialog; focus cancel; success removes inaccessible view | Preserve safe context, Escape/cancel leaves state unchanged |

Preview lifetime copy follows server metadata: SQLite preview resets on process restart; shared PostgreSQL preview keeps the same visitor until expiry. Both show the one-hour limit and synthetic-data warning. Access expiry does not promise immediate physical deletion or backup erasure; the deployment record defines delayed cleanup. Shared PostgreSQL is locally tested and its dedicated external connection is authorized; the external deployment remains unverified.

## Async and permission behavior

GET requests carry AbortSignal and ignore superseded responses. Chat/group changes poll every 3 seconds, plus explicit refetch after mutations/visibility changes. This is near-realtime polling, not websocket/push delivery. A failed read shows one persistent stale/offline banner and retry; it is never presented as synchronized. 401 clears session/private caches, 403 removes group content and explains access. Logout broadcasts to sibling tabs and cancels requests. No retry loop on authorization failure.

Lists are bounded/paged by the API. Earlier chat uses an explicit load-earlier action and stable message IDs. Late batches cannot replace the newly selected group. Data freshness is separate from message read cursor. Read advances only while the chat is visible and actually shown; notification arrival is not a read.

Browser back has stable routes for space/chat/events/event-detail/memories/settings. Modal cancel restores trigger focus. Dirty form/chat navigation prompts before discarding. Full unload uses beforeunload only when a draft exists. No secret or private message is persisted to localStorage for draft recovery.

## UI states and accessibility

Every route: initial loading, data/empty, readable error/retry, explicit forbidden/not-found, Korean document title. Mutations: idle/busy/success/error. Visible labels, keyboard focus, semantic buttons/links, no native dialogs, noValidate forms with inline errors. First invalid field receives focus and has aria-invalid plus existing help/error descriptions. Textareas have resize:none and adequate height. IME Enter does not send/submit before composition ends.

Target WCAG 2.2 AA, automated axe plus keyboard/contrast/mobile/reduced-motion checks. Actual assistive-technology/physical iOS/Android testing is not implied by desktop Chromium emulation. Touch targets approximately 44px; fixed navigation respects safe areas and cannot cover fields. Critical errors do not exist only in disappearing toast text.

## Evidence

Backend tests: tests/test_community*.py. Browser workflow and accessibility evidence: web/tests/*.spec.ts. Final screenshots and test report: docs/implementation/. These paths must be populated by actual executed checks before declaring implementation complete.
