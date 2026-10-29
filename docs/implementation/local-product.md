# Local product implementation — scope and assumptions

User authorization: 2026-10-29 23:54 Asia/Seoul, “개발까지 쭉 해봐”. This supersedes the earlier document-only/file-transfer restriction. The existing preparation documents are retained as research-stage records; they are not evidence that customer research passed.

## First working slice

Private group chat/announcements, recurring account/session use, invitation/join boundaries, create/join/cancel/capacity/attendance, nonmonetary shared assets from verified participation, coarse optional activity and a Korean mobile-first 2D clubhouse. Running and the local web platform are reversible implementation assumptions. No original harness code is repurposed as the consumer backend.

## Local architecture decision

React/TypeScript + Vite for a browser-verifiable client; FastAPI + SQLite for a durable local server. Existing Python tools and a local browser permit meaningful transaction/authorization tests without creating a third-party account. SQLite serializes seat transactions; this is a single-instance local product, not a claim about horizontal production scale. Node dependencies are isolated under web/, Python app modules under community/, data under ignored .harness/.

Local sessions are database-backed, credentials hashed, changes protected by CSRF and trusted local Origin. Demo login exists only under explicitly enabled DEMO_MODE and is clearly labeled. Use only synthetic data and test passwords. Social identity, email verification/recovery, external push, image upload, production moderation staffing, legal retention and deployment are not configured.

## Conservative implementation policies

- Public group space/activity starts off. Member contribution to activity requires a separate opt-in. Never send raw chat/identity/exact active counts or times to the public endpoint.
- Recent activity considers a previous completed fixed week after at least 24 hours delay and requires at least 5 distinct consenting active members, with per-person/day bounds. These are local test assumptions, not a proven anonymity guarantee. Ineligible/changed membership/consent fails closed. Public feature remains unsuitable for real data before privacy review.
- Chat is server-persisted, paged and polled with idempotent send keys. Polling must recheck membership; no websocket, OS push or encrypted-messenger equivalence is claimed.
- Seats are server-authoritative. Waiting members must explicitly accept a time-limited offered place. Server transactions and request IDs handle double taps, cancellation races and expiration.
- Only authorized organizers confirm attendance after the event starts, and cannot approve their own contribution. Corrected attendance updates contribution eligibility; messages never earn assets. Permanent memories do not decay when chat is quiet.
- Shared assets are finite, nonmonetary and group-owned in this local model. No cash, trading, NFT, individual leaderboards, health metrics or rest penalties.
- No image uploads or imported messages/contacts. Local test data stays in this environment. Real retention/erasure and organizational ownership require further decisions before real users.

## Verification and handoff

This implementation must pass scoped API tests, existing harness tests/lint, frontend lint/type/build, real Chromium mobile/desktop workflows, accessibility and screenshots. User research Gates 0–2 remain unvalidated; the user's explicit request authorizes a testable implementation, not public launch. Independent QA/security review is required for the final code.

Implementation status: API and client implemented; final local verification passed. See [verification results](verification.md). Independent review found four backend issues: spent-invite retry, muted seat-offer notification, negative attendance correction after departure, and seeded identity/session access when demo mode is disabled. All four were fixed, with 14 added regression cases; 33 service cases + 32 existing harness cases passed (65 total). Independent re-review confirmed the repairs. Browser testing also found stale session response and draft-navigation races; both were fixed and independently rechecked. Final browser suite: 9 passed. No push or deployment is authorized by this request.

## Policies represented by the API

A new membership has its own chat history boundary. Leaving and rejoining cannot recover an earlier membership's messages through a stale request. Current announcements and future events remain available to new members; previous events are not. Removing a member also invalidates current resource access and cancels future registrations. Group owners cannot leave until a future ownership-transfer feature exists.

Blocking hides ordinary chat messages mutually. It does not hide official announcements, member lists, or attendance details from an authorized organizer. Reports about an organizer cannot be resolved by that organizer. Message deletion leaves a tombstone and an audit entry; the private API no longer returns its original text. This is not a legal retention or physical-storage erasure guarantee.

Attendance counts at most one verified contribution per person per Asia/Seoul calendar day. Owners and organizers can confirm other participants after an event starts. Attendance corrections can remove erroneous contribution eligibility; quiet weeks never remove earned objects. The first implementation covers attendance, not automatic rewards for every possible helpful action. Collusion and community fairness still need product validation.

A 30-minute seat offer reserves capacity until acceptance or expiration. Expiration and promotion are computed on the next relevant server request; there is no background scheduler or push-delivery promise. Muting affects new in-app notifications, not the ability to inspect the event and accept an offer.

## Local limits and release boundary

- One SQLite database and one local API instance; no hosted service, scaling or availability claims.
- Local credentials and sessions only; no external identity verification, account recovery or verified real membership.
- Text chat, current announcements, event creation/cancellation and attendance; event editing, group creation, ownership transfer, account deletion, photos and production retention jobs are not implemented.
- Existing demo records are synthetic. A separate database is the clearest way to start another demonstration without deleting previous work.
- No real customer interviews, voluntary community migration or physical device tests have occurred. Native/PWA and public-launch decisions remain open.
- Before real users: account/retention/erasure decisions, abuse operations, real authentication and notification delivery, privacy review, hosting and explicit deployment authorization are required. No accounts or integrations are created as part of this local work.
