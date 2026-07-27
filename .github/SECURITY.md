# Security policy

## Reporting a vulnerability

**Please do not open a public issue for a security problem.** Public issues are
visible to everyone, including during the festival, when the app is carrying
live attendee data.

Report privately through GitHub:

**[Open a private security advisory](https://github.com/Arutemu64/fanapp/security/advisories/new)**

That creates a thread only the maintainers can see. If the link doesn't work,
private reporting isn't enabled yet — open a normal issue saying only that you
have a security report, **with no details**, and a private channel will be
opened for you.

## What to expect

This project is maintained by one person around a live event, so response time
depends on the calendar. Expect a first reply within about a week, and slower
during the festival itself. You'll be told whether the report is accepted and
when a fix ships. Reporters are credited in the advisory unless they'd rather
not be.

## Supported versions

The latest release is the only supported version. There is a single production
deployment and fixes ship forward — patches are not backported to older tags.

## Scope

In scope: the source code in this repository — the backend API, the SvelteKit
frontend, the Telegram bot, and the deployment configuration.

**The live festival deployment is not a testing target.** Do not scan it, probe
it, run automated tooling against it, or attempt to access accounts that aren't
yours. It serves real attendees, many of them minors, during an event where an
outage has physical consequences for people standing in a queue. Reports based
on testing against production will be handled as incidents rather than as
research.

Reproduce locally instead. `just bootstrap && just run-dev` brings up the whole
stack — API, frontend, bot, Postgres, Redis, NATS — with generated local
secrets and no real third-party credentials, so you can test freely against
your own instance. See the README for setup.

Also useful to report, though not vulnerabilities in themselves: a secret
committed to the repository, or a dependency advisory that actually reaches
production code paths.
