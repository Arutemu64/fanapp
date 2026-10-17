# Product analytics for FAN FAN: measuring which features get used

Researched 2026-10-17 against primary sources. The question: how to learn which
features of the companion PWA attendees use most, given the stack (SvelteKit SPA +
FastAPI + Postgres 18 on a 1-vCPU / 2 GB VPS, see `docs/deployment.md` "Sizing"),
an audience that includes minors, Russian users, and flaky venue networks.
Sections 1–4 are findings. Section 5 is a recommendation and is **inference**.

Repo facts this builds on: the frontend is a client-rendered SPA
([ADR-0007](../../docs/adr/0007-client-rendered-spa-frontend.md)), has a single
reachability service and an IndexedDB-backed query cache (`docs/frontend.md` §2),
and already ships Sentry/GlitchTip error reporting (`frontend/src/hooks.client.ts`).
Real usage arrives in two convention weekends a year (`docs/deployment.md`
"Error reporting during a convention"). I found no privacy-policy or consent copy in
`frontend/messages/ru.json`; it may live on the organiser's own site (unverified).

## 1. Measurement design

**Start from the question, then instrument the minimum.** Amplitude's planning
guide says to begin with "What metric are you trying to optimize?" and to "plan and
instrument your most important metrics, then iterate later to add more"
([Amplitude, data planning playbook](https://amplitude.com/docs/data/data-planning-playbook)).
For "which features are used most" the metric is a count of feature-level actions
per day, split by surface. That needs neither user identity nor session replay.

**Page views vs. custom events.** In an SPA, a route change is a cheap proxy for
"opened feature X". SvelteKit's `afterNavigate` runs "when the current component
mounts, and also whenever we navigate to a URL", and its target carries `route`,
`params` and `url` ([SvelteKit, `$app/navigation`](https://svelte.dev/docs/kit/$app-navigation)).
Logging `to.route.id` (e.g. `/(app)/voting/[nominationCode]`) instead of `url`
keeps nomination codes, query strings and any IDs out of the data by
construction. Page views cannot see in-page actions (subscribe to an event, cast a
vote, toggle push, open the map viewer, search the schedule), so those need custom
events.

**Naming.** Vendors differ on tense and case, so pick one and keep it:

- PostHog: lowercase snake_case, present-tense verbs, a fixed verb allowlist, and a
  `category:object_action` shape; names must be fixed strings, never built
  dynamically (`page_viewed` + a `page_name` property, not ``page_viewed_${pageName}``);
  version a name on a breaking change (`registration_v2:…`)
  ([PostHog, product analytics best practices](https://posthog.com/docs/product-analytics/best-practices)).
- Amplitude: "`Song Played`" and "`song played`" are two separate events, so
  consistency matters more than the particular style; prefer one event with a
  property over several near-duplicate events, so a new option doesn't require new
  charts ([Amplitude](https://amplitude.com/docs/data/data-planning-playbook)).
- Segment's tracking-plan page returned HTTP 403 to my fetch, so its "Object
  Action" guidance is unverified here.

**Properties and over-collection.** Keep properties enumerated and low-cardinality
(the surface, a mode such as `standalone` vs `browser`, an outcome such as
`ok` / `offline_blocked`). Plausible tells users they "must ensure that no
personally identifiable information (PII) is sent … with custom properties",
including "pseudonymous identifiers like cookie or advertising IDs", and warns that
a mistakenly sent value can only be removed by resetting the whole site's data
([Plausible, custom properties](https://plausible.io/docs/custom-props/introduction)).
Hard limits to design under: Plausible allows 30 properties per event, 300-char
names, 2,000-char values ([same page](https://plausible.io/docs/custom-props/introduction));
Umami allows 50 properties per event and 500-char strings
([Umami, tracker functions](https://docs.umami.is/docs/tracker-functions)).

## 2. Self-hostable, cookieless options

| | Umami 3.4.0 | Plausible CE 3.2.1 | Matomo 5.14.1 | PostHog (self-hosted) | Own table in Postgres |
| --- | --- | --- | --- | --- | --- |
| Licence | MIT ([LICENSE](https://github.com/umami-software/umami/blob/master/LICENSE)) | AGPL-3.0; tracker MIT ([repo](https://github.com/plausible/analytics)) | GPL-3.0 ([LICENSE](https://github.com/matomo-org/matomo/blob/5.x-dev/LICENSE)) | MIT outside `ee/` ([LICENSE](https://github.com/PostHog/posthog/blob/master/LICENSE)) | ours |
| Storage | PostgreSQL ≥ 12.14, Node ≥ 18.18 ([install](https://docs.umami.is/docs/install)) | ClickHouse (CPU needs SSE 4.2 / NEON) + Postgres, "at least 2 GB of RAM" recommended ([CE repo](https://github.com/plausible/community-edition)) | MySQL 8 / MariaDB 10.6, PHP 8.1; 2 CPU / 2 GB for ≤100k page views a month ([requirements](https://matomo.org/faq/on-premise/matomo-requirements/)) | ClickHouse, Kafka, ZooKeeper, MinIO…; "4 vCPU, 16GB RAM"; self-host "officially unsupported" ([self-host](https://posthog.com/docs/self-host)) | existing Postgres 18 |
| Fits the 2 GB VPS? | Yes, could share the Postgres server (inference) | No: its own recommendation consumes the whole host | No: needs a second database engine and its own 2 GB | No | Yes |
| Cookies | None ([FAQ](https://docs.umami.is/docs/faq)) | None, no local storage ([data policy](https://plausible.io/data-policy)) | Cookies by default; `disableCookies` turns them off ([FAQ](https://matomo.org/faq/general/faq_157/)) | Cookie + localStorage by default; `cookieless_mode: 'always'` must also be enabled in project settings ([config](https://posthog.com/docs/libraries/js/config)) | None |
| Visitor identifier | Deterministic UUID from site, IP, User-Agent and a salt that rotates monthly by default (`SALT_ROTATION`: day/week/month) ([source, `api/send/route.ts`](https://github.com/umami-software/umami/blob/master/src/app/api/send/route.ts), [env vars](https://docs.umami.is/docs/environment-variables)) | `hash(daily_salt + domain + ip + user_agent)`, salt deleted every 24 h, raw IP/UA never stored ([data policy](https://plausible.io/data-policy)) | Cookie ID, or a config hash without cookies (details unverified) | Server-side hash in cookieless mode; salt schedule not documented (unverified) | None needed for counts |
| SPA page views | Auto (history) | Auto with `pushState` routers ([SPA](https://plausible.io/docs/spa-support)) | Manual `trackPageView` per route (unverified for 5.x) | `capture_pageview: 'history_change'` ([config](https://posthog.com/docs/libraries/js/config)) | `afterNavigate` |
| Custom events | `umami.track(name, data)` ([docs](https://docs.umami.is/docs/tracker-functions)) | `plausible(name, {props})` ([docs](https://plausible.io/docs/custom-event-goals)) | `trackEvent` | `capture` | ours |
| Offline | None: the tracker sends with `fetch(…, {keepalive: true})` and swallows errors, so an offline event is lost ([source, `tracker/index.ts`](https://github.com/umami-software/umami/blob/master/src/tracker/index.ts)). The collect API accepts a client `timestamp`, so a custom queue can replay with the original time ([tracker functions](https://docs.umami.is/docs/tracker-functions)) | Not documented (unverified) | Service-worker offline queue: `queueLimit` 50, `timeLimit` 1 day, standard endpoints only ([FAQ](https://matomo.org/faq/how-do-i-set-up-matomo-offline-tracking/)) | Not documented (unverified) | IndexedDB queue we control |
| Tracker size (gzip, measured 2026-10-17) | 2.3 KB (`cloud.umami.is/script.js`) | 1.3 KB (`plausible.io/js/script.js`; vendor claims 2.5 KB, [page](https://plausible.io/lightweight-web-analytics)) | not measured | ~103 KB (`posthog-js@1.438.12` `dist/array.js`) | < 1 KB of our own code (inference) |

Notes:

- Umami also stores derived country, region and city per session (fields in the
  same `route.ts`), resolved from the IP or CDN headers
  ([env vars, `GEO_DATABASE_URL`](https://docs.umami.is/docs/environment-variables)).
  Its `identify()` / `data-distinct-id` links sessions to an ID you supply
  ([distinct IDs](https://docs.umami.is/docs/distinct-ids)); for this project that
  would tie analytics to accounts, which section 3 argues against.
- Umami has a `data-before-send` hook that can rewrite or drop any payload, plus
  `data-exclude-search`, `data-exclude-hash` and `data-auto-track="false"`
  ([tracker configuration](https://docs.umami.is/docs/tracker-configuration)), so it
  can be restricted to route IDs and named events.
- Plausible CE omits funnels, revenue goals, SSO and the sites API, and is community
  supported only ([README](https://github.com/plausible/analytics)).

**Sending from a phone.** `navigator.sendBeacon()` "is intended for analytics",
sends a POST, caps queued data at 64 KiB, and returns `true` only when the data was
*queued*, not delivered; send on `visibilitychange` → `hidden`, not on `unload` /
`pagehide`, which are unreliable and break the bfcache
([MDN, sendBeacon](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon)).
MDN calls the `hidden` transition "the last event that's reliably observable by
the page", including when a mobile user switches apps
([MDN, visibilitychange](https://developer.mozilla.org/en-US/docs/Web/API/Document/visibilitychange_event)).
`sendBeacon` is in every target browser (Safari since 11.1)
([browser-compat-data](https://github.com/mdn/browser-compat-data/blob/main/api/Navigator.json)).
Neither primitive survives being offline, though.

**Offline queueing.** Workbox Background Sync stores failed requests in IndexedDB
and replays them on the `sync` event, with `maxRetentionTime` bounding the queue;
without the Background Sync API it "will automatically attempt a replay whenever
your service worker starts up"
([Workbox, background sync](https://developer.chrome.com/docs/workbox/modules/workbox-background-sync)).
The API is "not Baseline"
([MDN](https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API)):
`SyncManager` ships in Chromium only, with no support in Firefox or Safari, iOS
included ([browser-compat-data](https://github.com/mdn/browser-compat-data/blob/main/api/SyncManager.json)).
For iPhone attendees, then, the replay depends on the app being opened again.

## 3. Legal: Russia (152-FZ)

Text checked on consultant.ru, revision of 26.07.2026. ConsultantPlus marks some
articles as having amendments prepared that are not yet in force, so re-check before
relying on any of this. **This is not legal advice. The organiser's lawyer should
confirm the conclusions.**

- **Definition.** Personal data is "любая информация, относящаяся к прямо или
  косвенно определенному или определяемому физическому лицу" (Art. 3 p. 1).
  Anonymisation (обезличивание) means attribution becomes impossible "без
  использования дополнительной информации" (Art. 3 p. 9)
  ([Art. 3](https://www.consultant.ru/document/cons_doc_LAW_61801/4f41fe599ce341751e4e34dc50a4b676674c1416/)).
- **Roskomnadzor on analytics.** Letter No. 08-242780 of 26.06.2024 says that if a
  site runs software that can "определить уникального посетителя сайта, формировать
  сведения о его предпочтениях и поведении на сайте (метрические программы), то
  данный факт указывает на обработку персональных данных". The operator must then
  inform the visitor, obtain consent, and describe the processing in a local act. The
  letter also treats Google Analytics as cross-border transfer requiring notification
  under Art. 12 p. 3 ([text on garant.ru](https://www.garant.ru/products/ipo/prime/doc/409415443/)).
  This is a letter answering one enquiry, not a normative act. I found no newer
  official RKN clarification. Commercial blogs claim stricter 2026 enforcement
  against cookie banners, which is unverified. Reading this letter, any tool that
  derives a per-visitor ID (Umami's monthly UUID, Plausible's daily hash, Matomo,
  PostHog, Metrica) plausibly counts as a "metric program". Anonymous event counts
  with no visitor identifier probably do not (inference).
- **Legal bases.** These include consent (Art. 6 p. 1 item 1), performance of a
  contract with the subject (item 5), the operator's legitimate interests where the
  subject's rights are not infringed (item 7), and statistical or research purposes
  "при условии обязательного обезличивания" (item 9)
  ([Art. 6](https://www.consultant.ru/document/cons_doc_LAW_61801/315f051396c88f1e4f827ba3f2ae313d999a1873/)).
  RKN's letter assumes consent for metric programs.
- **Consent form (from 1 Sept 2025).** Consent must be "конкретным, предметным,
  информированным, сознательным и однозначным", and since Federal Law 156-FZ of
  24.06.2025 it "должно быть оформлено отдельно от иных информации и (или)
  документов" ([Art. 9](https://www.consultant.ru/document/cons_doc_LAW_61801/6c94959bc017ac80140621762d2ac59f6006b08c/)).
  Art. 5 of that law took effect on 1 September 2025
  ([156-FZ, Art. 7](http://www.kremlin.ru/acts/bank/52029)). A checkbox buried in
  terms of use no longer counts as consent.
- **Localisation (from 1 July 2025).** Under Federal Law 23-FZ of 28.02.2025, Art. 18
  p. 5 reads: when collecting data, "в том числе посредством … сети "Интернет"",
  recording, systematisation, accumulation, storage, clarification and extraction of
  RF citizens' data "с использованием баз данных, находящихся за пределами
  территории Российской Федерации, не допускаются", except for Art. 6 p. 1 items 2,
  3, 4 and 8
  ([Art. 18](https://www.consultant.ru/document/cons_doc_LAW_61801/cbf4e15b7c330f9372e876cdf2bc928bad7950ef/)).
  The law took effect "с 1 июля 2025 года"
  ([23-FZ, Art. 10, garant.ru](https://www.garant.ru/products/ipo/prime/doc/411474151/)).
  Any foreign-hosted analytics SaaS (Plausible Cloud, PostHog Cloud, GA) is
  therefore ruled out for identifiable data. A self-hosted tool is acceptable only on
  a server in Russia, and I have not verified where the production VPS is located.
  The same question applies to the existing Sentry/GlitchTip sink, which receives
  IPs (inference).
- **RKN notification.** The operator must notify RKN before processing (Art. 22 p. 1).
  Since 266-FZ the old exemptions in items 1–6 are repealed, leaving only state
  systems, non-automated processing and transport security. The notice must state
  the purpose of processing and "сведения о месте нахождения базы данных", and any
  change must be reported "не позднее 15-го числа месяца, следующего за месяцем, в
  котором возникли такие изменения" (Art. 22 pp. 3, 7)
  ([Art. 22](https://www.consultant.ru/document/cons_doc_LAW_61801/d996966e22e1320c9de1ab82d9f6be12c3d9d765/)).
  The app already holds accounts, so the organiser should already have filed a
  notice (unverified). Adding identifiable analytics would add a purpose that needs
  reporting (inference).
- **Published policy.** An operator collecting data online "обязан опубликовать" its
  processing policy on the site and provide access to it (Art. 18.1 p. 2)
  ([Art. 18.1](https://www.consultant.ru/document/cons_doc_LAW_61801/eeeebe22bf738fd65bb66b95cc278911ae2525ee/)).
- **Minors.** 152-FZ sets no age threshold. Art. 9 p. 6 assigns consent to a legal
  representative only for a legally incapable subject
  ([Art. 9](https://www.consultant.ru/document/cons_doc_LAW_61801/6c94959bc017ac80140621762d2ac59f6006b08c/)).
  Practice borrows the Civil Code's capacity rules: under-14s act through parents
  (Art. 28), and 14–18-year-olds act with a representative's written consent
  (Art. 26). That summary comes from ConsultantPlus commentary, not the article text
  ([ConsultantPlus selection](https://www.consultant.ru/law/podborki/gk_sdelki_nesovershennoletnih/)).
  Whether an analytics consent from a 14–17-year-old is valid on its own is
  **uncertain**. Collecting nothing identifiable avoids the question.
- **Yandex Metrica.** It is the local default and is processed in Russia, but under
  its terms (published 07.08.2026) the site owner "является оператором персональных
  данных, а Яндекс – лицом, действующим по поручению оператора". The owner must inform
  visitors and obtain consent where the law requires it (cl. 2.1, 5.4). Yandex may
  use aggregated data "по своему усмотрению, в том числе и в коммерческих целях"
  (cl. 5.3)
  ([Metrica terms](https://yandex.ru/legal/metrica_termsofuse/)). It sets `_ym_uid`
  and similar cookies for one year and has no cookieless mode
  ([Metrica cookies](https://yandex.ru/support/metrica/general/cookie-usage.html)).
  It would need a separate consent, a policy update, and a Yandex script on a site
  for minors. That is disproportionate for feature counts (inference).
- **GDPR.** It reaches non-EU controllers only when they offer goods or services to,
  or monitor the behaviour of, people in the EU (Art. 3(2),
  [Regulation 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)). A Russian
  convention app is unlikely to be in scope (inference).

## 4. Engineering concerns

- **Ad blockers.** PostHog says a first-party reverse proxy "typically increases
  event capture by 10-30%". It advises against path or subdomain names such as
  `analytics`, `tracking`, `telemetry`
  ([PostHog, proxy](https://posthog.com/docs/advanced/proxy)). Plausible estimates
  strict blockers hide "5% to 25%" of visitors without a proxy, and says a proxy must
  forward the real IP in `X-Forwarded-For` or bot filtering drops events
  ([Plausible, proxy](https://plausible.io/docs/proxy/introduction)). Umami supports
  `TRACKER_SCRIPT_NAME` and `COLLECT_API_ENDPOINT` for the same purpose
  ([env vars](https://docs.umami.is/docs/environment-variables)). Our Caddy already
  puts the API on the same origin (`docs/deployment.md` "Reverse proxy"), so a
  first-party `/api/...` endpoint looks no different from any other app call
  (inference).
- **Performance.** web.dev: "Always use `async` or `defer` for third-party scripts",
  but async loading "won't prevent them from slowing down page load"; on the other
  hand, deferring analytics too long can "miss valuable analytics data"
  ([web.dev, third-party JS](https://web.dev/articles/optimizing-content-efficiency-loading-third-party-javascript)).
  The 1–2 KB trackers are negligible next to the shell. A ~100 KB `posthog-js` is
  not (sizes measured above).
- **Sampling.** Event volume is bounded by two weekends a year, so there is no
  reason to sample. This matches the 100% Sentry sampling advice already in
  `docs/deployment.md` (inference).
- **Retention and aggregation.** Keep raw events briefly, then roll them up into
  daily counts. In Postgres, partitioning by time makes expiry a `DROP TABLE` /
  `DETACH PARTITION`, which "is far faster than a bulk operation" and avoids
  `VACUUM` overhead from bulk `DELETE`
  ([PostgreSQL 18, partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)).
  BRIN suits large append-only tables whose column correlates with physical order,
  such as an insertion timestamp
  ([PostgreSQL 18, BRIN](https://www.postgresql.org/docs/current/brin.html)). At this
  volume, a plain table with a periodic `DELETE` is likely enough (inference).
- **No account IDs.** "Which features are used most" is answered by counts. Joining
  to `users.id` turns a feature counter into a behavioural profile of a named and
  possibly minor attendee, which is exactly the RKN letter's trigger. Don't add
  `user_id`, a persistent device ID, IP or User-Agent. If you need "how many
  people", the coarse `is_authenticated` flag plus daily totals is enough (inference).

## 5. Recommendation for this repo (inference)

Build a **first-party, anonymous event counter** on the existing stack instead of
adopting a third-party tool. Why: every off-the-shelf option derives a per-visitor
identifier (section 2), which RKN reads as personal data needing separate consent
(section 3) on a site used by minors. Plausible CE, Matomo and PostHog don't fit the
2 GB host. None of them except Matomo queues offline, and Matomo's queue is
time-limited to one day. Our own endpoint inherits same-origin routing (no ad-block
loss), the Russian-hosted Postgres, and the app's reachability service. If the team
later wants dashboards and visitor counts, Umami on the same Postgres server is the
lightest fallback. Treat it as a "metric program": separate consent and a policy
update first.

Ordered minimal rollout:

1. **Write the question list and a tracking plan** of 10–15 events in a
   `category:object_action` / snake_case scheme with a fixed verb list (PostHog
   style). Examples: `page_view` with `route_id`, `schedule:event_subscribe`,
   `voting:vote_submit`, `push:enable`, `map:open`, `guide:article_open`,
   `quest:award_view`, `offline_write:blocked`. Use enumerated properties only. Add
   it to `GLOSSARY.md` or a doc, plus an ADR (new data flow, privacy stance).
2. **Backend**: `POST /api/telemetry/events` accepting a small batch of
   `{name, route_id?, props, client_ts}`. Validate `name` against a server-side
   allowlist and props against enums, and reject anything else. Store `(day, name,
   route_id, props jsonb, app_version, display_mode, is_authenticated)` with no IP,
   no UA and no user ID, which means not using the auth dependency for anything but
   the boolean. Rate-limit per connection. Bound `client_ts` to the queue's retention
   window.
3. **Frontend**: a tiny `track()` in `#lib/services/` that appends to an IndexedDB
   queue (same `idb-keyval` already used by the query persister). Flush the batch
   when `reachability.current` is reachable and on `visibilitychange → hidden`
   via `sendBeacon` / `fetch(…, {keepalive: true})`. Cap the queue (e.g. 200 events,
   48 h) and drop the oldest. Don't rely on Background Sync, since it is
   Chromium-only. Record page views from `afterNavigate` using `to.route.id`. The
   queue holds no user data, so `Session` needn't reset it, though resetting on
   logout costs nothing.
4. **Retention**: a scheduler job (the APScheduler host already exists) rolls raw
   rows into a `telemetry_daily_counts` table and deletes raw rows older than e.g. 30
   days. Keep the counts indefinitely, so seasons can be compared.
5. **Reading**: start with SQL or a small organiser-only tools page that ranks
   events by count per convention day. Suppress cells with tiny counts if the page
   ever shows rare features.
6. **Legal check before launch**: confirm with the organiser where the VPS is
   hosted (Art. 18 p. 5) and that the RKN notice and published policy cover
   "статистика использования функций приложения в обезличенном виде". Have a lawyer
   confirm that identifier-free counts are outside the RKN letter. Only then
   consider anything identifier-based (Umami, Metrica), with a separate consent
   screen.
