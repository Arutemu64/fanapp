# ADR-0024: DiceBear avatars drawn in the browser from a stored seed

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** project maintainers

## Context

Avatars were the first letters of the username on a tinted circle. Two users
with similar names looked alike, and people had no way to make the circle
theirs. We have no image uploads and do not want them: storage, moderation and
resizing for a convention app are far more than a picture is worth.

## Decision

We will draw every avatar from a short per-user seed with the DiceBear
[Initial Face](https://www.dicebear.com/styles/initial-face/) style (CC0).

- `users.avatar_seed` stores the seed; the user rerolls it in the profile
  editor and the new value is saved with the rest of the form
  (`PATCH /me`, `avatar_seed`, validated against `AVATAR_SEED_PATTERN`).
- Rendering is client-side with `@dicebear/core` and the `@dicebear/styles`
  definition (about 7 KB), not the hosted HTTP API. The app works offline,
  no seed or username leaves the app, and no third party sits on the request
  path.
- The client proposes the seed rather than the server rerolling on a
  dedicated endpoint, so the editor can preview a face and drop it on cancel.
  The seed is not a secret, only a stable input to the generator.

## Consequences

- Existing users get a random seed from the migration's backfill.
- Organiser screens (`UserListItemDTO`, `UserDetailsDTO`) carry the seed so
  they show the same face the user sees.
- Output is deterministic per seed, style and library version. A major
  DiceBear upgrade can change every face at once; pin and bump deliberately.
