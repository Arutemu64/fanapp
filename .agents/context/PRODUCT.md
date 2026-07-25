# Product

## Register

product

## Users

Teen to young-adult anime fans attending the "FAN FAN" Russian anime convention, plus the organizers who run it. Non-technical audience, almost always on a phone, often on flaky con-venue wifi, in a hurry between events. Attendees come to check the schedule, subscribe to events, vote, read notifications, and manage their ticket-linked profile. Organizers use the same app to manage and import the schedule, run voting, and broadcast notifications. All user-facing copy is Russian.

## Product Purpose

A mobile-first companion web app (PWA) that puts the whole convention in the attendee's pocket: live event schedule with subscriptions, nominations and voting, an in-app notification feed plus Web Push, and ticket-linked profiles with account connections and security settings. Success = an attendee can find what's happening next, get notified when it changes, and vote — in seconds, one-handed, without thinking about the tool. For organizers, success = running the schedule and broadcasts without leaving the same surface.

## Brand Personality

Clean and friendly. Approachable, trustworthy, easy. Three words: **clear, lively, calm-under-load**. The watermelon palette (crimson-pink primary, cyan-teal secondary) carries the fandom energy and warmth; the layout and interaction stay calm and uncluttered so a tired attendee can scan it at a glance. Color is the personality; structure is the restraint. Not loud, not maximalist — the vibrance lives in accents and moments, not in shouting at every screen.

## Anti-references

- **Childish / cartoonish.** No comic-sans energy, no sticker overload, no talking down to teens. The audience is young but wants to be taken seriously.
- **Generic AI template.** No cream/sand body background, no tiny uppercase tracked eyebrows over every section, no identical icon-card grids, no gradient text. Avoid the 2026 slop look.
- **Cluttered / overwhelming.** No wall of information, no cramming. Phone-first means breathing room, clear hierarchy, one primary thing per screen.

(Corporate/enterprise SaaS sterility was deliberately *not* ruled out — a degree of clean professionalism is welcome, just warmed by the brand color.)

## Design Principles

1. **One-handed, one-glance.** Every primary task readable and reachable on a phone, thumb-first, in seconds. Bottom-anchored navigation, generous tap targets, scannable hierarchy.
2. **Color carries the joy, structure carries the calm.** Let the watermelon palette do the emotional work in accents, states, and key moments; keep layout quiet and uncluttered so it never overwhelms.
3. **Resilient by default.** Con wifi is bad. Skeletons over spinners, cached-shell offline boot, optimistic-but-honest states, never a blank or broken screen. Loading and error states are first-class, not afterthoughts.
4. **Consistent affordances.** Same button, same form control, same icon style across schedule, voting, profile, settings. The tool disappears into the task; surprise is saved for moments, not pages.
5. **Russian-native, plain-spoken.** Copy is warm, direct, and human in Russian — never jargon, never machine-translated stiffness.

## Accessibility & Inclusion

Target **WCAG AA**. Body text ≥4.5:1, large text ≥3:1 against its background; brand fills (600+ shades) already darkened so white text on a fill clears AA. Full `prefers-reduced-motion` support (CSS + JS-driven Svelte transitions both honor it — already in place). Visible keyboard focus states on every interactive element. Don't rely on color alone to convey state (pair with icon/text). Dark mode supported.
