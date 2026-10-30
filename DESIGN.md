---
version: alpha
name: ourcommunity
description: A Korean running clubhouse where private conversations and shared participation build a place together.
colors:
  primary: "#2448C8"
  ink: "#18232B"
  muted: "#596672"
  background: "#F4F6F8"
  surface: "#FFFFFF"
  border: "#D5DCE2"
  meadow: "#E5EBCD"
  sky: "#EAF0FF"
  clay: "#A95636"
  danger: "#A72C34"
  focus: "#1649D8"
typography:
  body:
    fontFamily: '"Noto Sans KR Variable", "Apple SD Gothic Neo", sans-serif'
  display:
    fontFamily: '"Outfit Variable", "Noto Sans KR Variable", sans-serif'
rounded:
  control: "0.5rem"
  panel: "0.75rem"
  dialog: "1rem"
spacing:
  field: "1rem"
  section: "2rem"
  page: "2.5rem"
components:
  button:
    backgroundColor: "#2448C8"
    textColor: "#FFFFFF"
  panel:
    backgroundColor: "#FFFFFF"
    textColor: "#18232B"
  dialog:
    backgroundColor: "#FFFFFF"
    textColor: "#18232B"
---

# ourcommunity Design System — Clubroom trial

## Overview

The 2026-10-30 user feedback rejects the previous mint/cabin direction. This trial follows the recovered Design Intelligence/Frontend Design Premium workflow; it is not a claim that the user selected a palette. [Reference decisions](docs/design-docs/ourcommunity-redesign/references.md) distinguish user evidence, provisional taste, official descriptions and unobserved source catalogs.

North Star: a Korean mobile sports club where conversation and the next commitment are immediately usable, and shared contributions change an inspectable communal place. People, content, actions and state take priority over large introductions. No repeated cabin hero, fake online counts, generic dashboard metrics or message-volume rewards.

## Colors

Paper/white surfaces with charcoal text provide the stable reading plane. Cobalt is reserved for action, focus and confirmed state; pale blue is its supporting surface. Meadow is limited to the communal map; clay is retained for compatibility with legacy illustrations. Danger remains distinct. Color never replaces status text. Palette is a trial implementation, not a globally inferred user preference.

## Typography

Self-hosted Noto Sans KR for Korean UI and Outfit for the restrained wordmark. Core text 14–16px, fields 16px, section headings 15–20px, page headings 23–27px. Metadata 11–12px; compact demo disclosure 10–11px. Avoid giant poetic headings and overly small primary content. Korean line-height and wrap remain deliberate; no decorative all-caps paragraphs.

## Layout

Desktop: 208px navigation, 58px context bar, conversation on the left, next-event and communal growth on the right. Mobile: four primary destinations and a separate settings shortcut. Home orders conversation then next meeting then shared place. Chat alone owns a bounded viewport: header and composer stay in place, messages scroll. Forms and settings retain document scrolling. Safe areas and short/keyboard-sized viewports are tested.

## Elevation & Depth

Object relationships use rows, rules and typography. Panels separate genuinely different tasks; avoid uniform decorative card stacks. Shadows belong only to floating dialogs/toasts. Demo limitations remain visible in a compact global strip; storage failures stay persistent.

## Shapes

Controls 8px, panels 12px, dialogs 16px. Date tiles and asset objects use stable geometry with purpose. No pill or leaf-icon decoration. The shared place uses a path, three inspectable objects and explicit placement controls, not a large scenic illustration.

## Components

Canonical Button/Field/Dialog/Confirm/Toast remain in `web/src/components/ui.tsx`. `MeetingAction` exposes the actual next event's RSVP state with pessimistic confirmation. `SharedSpace` owns read-only previews and the browser-demo placement editor. `AssetIcon` is the common object vocabulary. Map objects have keyboard alternatives; placement saves are reversible and failures preserve the old view. Existing permissions remain enforced by each data mode.

## Do's and Don'ts

- Keep current participation, state and next action before explanation.
- Connect attendance to an earned object and a visible placement change; keep recent activity separate.
- Preserve IndexedDB version/data, routes, backend behavior, draft/error/confirmation recovery.
- Do not pretend the browser demo is real multi-user messaging or that disabled aggregation is live.
- Do not treat static audit success or screenshots as user taste approval.

Token ownership: Model A. This frontmatter generates `web/src/tokens.css` with `scripts/generate_tokens.py`. Existing CSS provides baseline primitives/legacy routes; `web/src/redesign.css` owns the documented Clubroom layout and density variants. Both consume the same generated tokens. Future consolidation must preserve behavior and pass both browser suites.
