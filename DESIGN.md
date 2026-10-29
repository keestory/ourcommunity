---
version: alpha
name: ourcommunity
description: A Korean running clubhouse where private conversations and shared participation build a place together.
colors:
  primary: "#28594F"
  ink: "#203D3B"
  muted: "#5D716C"
  background: "#F3F6F2"
  surface: "#FFFFFF"
  border: "#DCE5DD"
  meadow: "#E2EDCF"
  sky: "#E9F1EE"
  clay: "#AC603D"
  danger: "#AB3D32"
  focus: "#23645A"
typography:
  body:
    fontFamily: '"Noto Sans KR Variable", "Apple SD Gothic Neo", sans-serif'
  display:
    fontFamily: '"Outfit Variable", "Noto Sans KR Variable", sans-serif'
rounded:
  control: "0.75rem"
  panel: "1.25rem"
  dialog: "1.5rem"
spacing:
  field: "1rem"
  section: "2rem"
  page: "2.5rem"
components:
  button:
    backgroundColor: "#28594F"
    textColor: "#FFFFFF"
  panel:
    backgroundColor: "#FFFFFF"
    textColor: "#203D3B"
  dialog:
    backgroundColor: "#FFFFFF"
    textColor: "#203D3B"
---

# ourcommunity Design System

## Overview

North Star: a small riverside running club's shared cabin and meeting board, drawn as a calm 2D outdoor scene. The illustration is the expressive center; messaging, attendance and safety controls use familiar product behavior. This is a reversible implementation direction authorized for a local first product, not a tested brand or platform decision.

Audience: Korean-speaking people who run together. Korean locale `ko-KR`, domain display timezone `Asia/Seoul`. Korea/running remain research assumptions. Product register throughout; no promotional landing-page feature grid. No Japan market or locale assumption.

The signature is a single panoramic clubhouse: trail, cabin, benches and growing shared memorials. Its assets correspond to server-confirmed group growth. It never draws one avatar/window per online user. A quiet scene remains complete, and recent activity cannot decay earned memories.

Token ownership: Model A. This file's frontmatter generates `web/src/tokens.css` through the repository's `scripts/generate_tokens.py`. Colors map to `--color-<name>`, typography to `--font-<role>`, rounded to `--radius-<name>`, spacing to `--space-<name>`. Feature CSS consumes those variables. The illustration may use named palette roles and tonal variants, not separate screen themes. Generation and a check mode prevent drift.

## Colors

Forest green is action and identity, meadow is a communal earned-state accent, sky is the outdoor scene background, clay is a restrained cabin/wayfinding accent. White surfaces and dark green ink keep Korean copy legible. Muted text remains readable. Danger is confined to irreversible or permission-removing actions. Focus uses a distinct outline, never color alone. Only a light theme is implemented; forced colors remains usable.

## Typography

Self-host Noto Sans KR for Korean body/controls and Outfit for the small Latin wordmark and occasional numeric display. Both use sans fallbacks. Body 15–16px with 1.65 line-height; headings 26–36px, restrained bold weight. Use `word-break: keep-all` plus overflow wrapping for long user messages. No faux italic Korean, all-caps paragraphs or decorative monospace labels.

## Layout

Desktop: 232px navigation, a spacious central column and contextual next-meeting/announcement area. Main content max width 1280px. A single large scene leads the home view; schedule and earned objects have different visual roles. Below 900px navigation becomes a bottom bar with visible Korean labels. Below 600px content uses 18px gutters; scene stays readable without horizontal scrolling. Forms own document scrolling, while a chat log may own a bounded scroll region. Do not constrain all routes to a fixed viewport.

## Elevation & Depth

Hierarchy comes from surfaces and spacing, with subtle shadows reserved for floating dialogs/toasts and the illustrated cabin. Avoid glass effects and gradients as generic decoration. A dialog backdrop clearly dims inert content. Inline errors and feedback reserve space rather than shifting primary controls.

## Shapes

Controls have a 12px radius, major scene/panels 20px, modal 24px. Use circles for avatars/status illustrations only. Avoid making every label a pill. Flat list rows and hairlines separate messages/events without enclosing everything in a card.

## Components

Shared owners: `web/src/components/ui.tsx` for Button, Field, EmptyState, ErrorState, Dialog and Toast; `web/src/lib/api.ts` for requests; `web/src/lib/format.ts` for Korean/KST formatting. Owner paths describe the intended implementation and are verified before completion.

Primary actions use forest fill, secondary actions borders, destructive confirmation uses danger. Buttons preserve width while busy and have hover/pressed/focus/disabled styles. Icon-only controls require Korean accessible labels. Fields own inline errors, labels and invalid focus. Passwords have a reveal toggle. Native select and datetime-local popups are intentionally OS-owned in this local prototype; display and API interpretation use explicit KST.

Lucide outline icons use a consistent 1.7–2 stroke. Actual button text remains visible on mobile. Status feedback is one shared live region; errors remain inline with recovery. Native browser alert/confirm/prompt are forbidden. Native HTML dialog supplies modality/inertness, with app-owned contents, focus restoration, Escape and safe cancel-first focus.

Motion is subtle opacity/transform feedback only. Scene changes should be understandable without movement. `prefers-reduced-motion` disables decorative motion and smooth scrolling. No perpetual badges or online-presence animation.

Voice: short, useful Korean. Actions are ‘참가 신청’, ‘신청 취소’, ‘출석 확인’, ‘공지 올리기’, ‘다시 시도’. A seed/demo label appears wherever sample identities could be mistaken for real activity. No fake realtime participant counts, conversion figures or customer claims.

## Do's and Don'ts

- Do connect every earned shared object to verified nonmonetary participation, and distinguish permanent memories from recent atmosphere.
- Do keep chat drafts on screen after network failure and require server confirmation before success.
- Don't expose private chat, personal activity, exact presence or health data through the scene.
- Don't reward message volume, rank individuals, punish rest, imply production authentication, or turn this into a generic metrics dashboard.
