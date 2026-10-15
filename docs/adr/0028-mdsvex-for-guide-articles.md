# ADR-0028: mdsvex for guide articles

- **Status:** Accepted
- **Date:** 2026-10-15
- **Deciders:** project maintainers

## Context

The Гид tab grew a "Чем заняться" section: one page per festival activity
(stage, fair, authors' alley, stands, contests, games and photo zones). Each is
a few paragraphs and lists of prose that organizers will reword and extend
before every festival. [ADR-0027](0027-paraglide-js-for-user-facing-copy.md)
keeps UI strings in `messages/ru.json`, which suits labels and short sentences
but not headings, paragraphs and bullet lists: every paragraph would become a
numbered message key, and nobody could read or review an article as a whole.

## Decision

We will write guide articles as Markdown files in `frontend/src/content/guide/`
and compile them with [mdsvex](https://mdsvex.pngwn.at) (0.12.x, Svelte 5
peer range) as a Svelte preprocessor.

- Frontmatter carries `title`, `description`, `icon` (a key into `ICONS` in
  `#lib/data/guideArticles.ts`) and `order`. The file name is the URL slug
  (`/guide/<slug>`).
- `guideArticles.ts` reads the files with an eager `import.meta.glob`, so every
  article is in the main bundle and opens offline with the rest of the guide.
- The route `guide/[slug]` renders the compiled component; the element styling
  lives on the wrapper, since the Markdown emits bare elements.
- ADR-0027 still governs everything else: chrome around the articles (section
  headings, back label, document title) stays in `ru.json`. Only the article
  body and its frontmatter live in Markdown, and they follow the same Russian
  copy rules ([.agents/redpolitika.md](../../.agents/redpolitika.md)).

## Consequences

- Adding or rewording an activity is a Markdown edit, reviewable as prose; a new
  file appears in the hub on its own.
- A content change still needs a build and deploy, as any copy change does.
- The articles are plain content: no Svelte components inside them, so a page
  that needs interactivity is a route, not an article.
- mdsvex bundles older unified/remark dependencies; it is a dev dependency used
  at build time only, so none of it reaches the client.
- Articles bypass the copy-tells scan in `fanfan-russian-copy`, which greps
  `ru.json` and the email templates; run it by hand over `src/content/`.

## Alternatives considered

- **Messages in `ru.json`.** Rejected: one key per paragraph and per list item,
  no way to read an article in one piece.
- **Plain `.md` loaded raw and rendered with a runtime Markdown parser.**
  Rejected: ships a parser to every phone for static text mdsvex compiles away.
- **A backend/CMS-managed article store.** Rejected for now: needs an editor UI,
  an API and offline caching for a few static pages that change once a year.
