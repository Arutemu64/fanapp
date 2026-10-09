import { PUBLIC_API_URL } from '$app/env/public';
import * as Sentry from '@sentry/sveltekit';
import { createContext } from 'svelte';

import type { NotificationDto } from '#lib/api/generated/index.js';

import {
	isReachable,
	markReachable,
	onReachableChange,
	probeReachability
} from '#lib/services/reachability.js';
import { requestReconnectRefresh } from '#lib/utils/reconnectRefresh.js';

const [getEvents, setEvents] = createContext<EventsClient>();

/**
 * Ceiling for the reconnect backoff. The stream never gives up: one that stays
 * broken while the backend is otherwise healthy — a carrier proxy that kills
 * long-lived connections, say — produces no reachability change for any other
 * path to hook, so only its own retries can ever bring realtime back.
 */
const MAX_RECONNECT_DELAY_MS = 60000;
/** After this many failed dials in a row, file one Sentry issue for the outage. */
const REPORT_AFTER_ATTEMPTS = 10;
/** Wait briefly before reconnecting after auth changes to avoid flicker during navigation. */
const RESTART_DEBOUNCE_MS = 250;
/**
 * If the dial stalls this long, treat the attempt as failed and reconnect. The
 * window covers DNS + TCP + TLS + response headers on a cold connection, which
 * on a congested venue cell is legitimately slow. It exists to catch a *hung*
 * dial — a server or proxy that accepts the connection but never sends headers,
 * firing neither onopen nor onerror for minutes — not a slow one, so it is set
 * well past plausible slowness: timing out a merely-slow network makes things
 * worse, since every retry restarts the whole dial.
 */
const DIAL_TIMEOUT_MS = 15000;
/**
 * Re-armed once the transport opens, so the backend handshake gets its own
 * window. Tighter than the dial: the connection already exists by then, and
 * `connection_established` is the first thing the backend writes to the stream.
 */
const HANDSHAKE_TIMEOUT_MS = 5000;
/**
 * Reconnect when nothing arrives on the stream for this long. The backend emits
 * a named `ping` event after 15s of idle time (HEARTBEAT_INTERVAL_SECONDS in
 * backend/src/fanfan/presentation/web/routes/sse.py), so a healthy connection
 * always delivers *something* within that window. The browser cannot see the
 * transport die without a clean close (Wi-Fi roaming, NAT timeouts), so this
 * watchdog is the only thing that notices a silently dead stream. 3x the ping
 * interval tolerates slow networks and timer jitter.
 */
const HEARTBEAT_TIMEOUT_MS = 45000;
/**
 * On foregrounding, a stream that heard nothing for longer than two server pings
 * is redialled at once rather than left to the watchdog. iOS 18 can resume a
 * suspended PWA with its EventSource still `OPEN` but dead, and no `error` event
 * ever fires (https://developer.apple.com/forums/thread/765183).
 */
const STALE_ON_RESUME_MS = 30000;
/**
 * Pause the stream once the app has been backgrounded this long. Web Push covers
 * notifications while hidden, so holding SSE open only churns the mobile radio.
 * The grace window avoids thrashing on quick app-switches (following a link out
 * and straight back).
 */
const HIDDEN_PAUSE_GRACE_MS = 60000;

export interface EventsHandshakePayload {
	server_time: string;
	authenticated: boolean;
	connection_id: string;
}

// Broadcast whenever a vendor sync run changes state. Carries just enough to
// log or filter; subscribers refetch GET /sync/sources rather than trusting it
// as the source of truth, so a missed event self-heals on the next reconnect.
interface SyncRunUpdatedPayload {
	source: string;
	status: string;
}

/**
 * Maps each SSE event name to the shape of its parsed payload.
 * `void` means the event carries no usable data (handler called with `undefined`).
 *
 * This is the frontend source of truth for SSE event names; it mirrors the
 * backend `SSEEventName` enum (backend/src/fanfan/application/dto/realtime.py).
 * Keep the two in sync by hand — SSE events are not in the OpenAPI spec, so
 * there is no code generation between them. Each key here must match an enum
 * value exactly (snake_case, no dots).
 */
interface SSEEventMap {
	connection_established: EventsHandshakePayload;
	schedule_updated: void;
	notification_created: NotificationDto;
	sync_run_updated: SyncRunUpdatedPayload;
	config_updated: void;
	ping: void;
}

export type SSEEventName = keyof SSEEventMap;

// Runtime list of every SSE event name. EventSource only surfaces events that
// have a listener attached, so the client attaches a watchdog-feeding listener
// for all known names even when no page subscribed — otherwise traffic the
// client isn't listening for would look like silence and trip the watchdog.
// The `satisfies` check forces this list to stay exhaustive against SSEEventMap.
const ALL_SSE_EVENTS = Object.keys({
	connection_established: true,
	schedule_updated: true,
	notification_created: true,
	sync_run_updated: true,
	config_updated: true,
	ping: true
} satisfies Record<SSEEventName, true>) as SSEEventName[];
export type SSEHandler<K extends SSEEventName> = (data: SSEEventMap[K]) => void;

interface RegisteredListener {
	handler: unknown;
	wrapper: EventListener;
}

/** Parse a raw SSE data string into a payload. Empty string → undefined; non-JSON → raw string. */
function parseEventData(raw: unknown): unknown {
	if (typeof raw !== 'string' || raw.length === 0) return undefined;
	try {
		return JSON.parse(raw);
	} catch {
		// A non-JSON payload means the backend broke the event contract; surface
		// it here instead of letting a typed handler fail somewhere downstream.
		console.warn('SSE event payload is not valid JSON', raw);
		return raw;
	}
}

/**
 * SSE (Server-Sent Events) client with automatic reconnection. It reports no
 * state to the UI: reachability (`reachability.ts`) is what the user sees, and a
 * lost stream just keeps retrying in the background.
 *
 * Usage:
 *   const client = getEventsClient();
 *   client.on('schedule_updated', handler);
 *   // cleanup:
 *   client.off('schedule_updated', handler);
 */
export class EventsClient {
	#source: EventSource | null = null;
	#reconnectAttempts = 0;
	// A pending connect: a backoff retry or the restart debounce.
	#dialTimerId: ReturnType<typeof setTimeout> | null = null;
	// One watchdog for whichever stage is live — the dial, the handshake, or the
	// open stream's heartbeat — since only one can be at a time.
	#watchdogId: ReturnType<typeof setTimeout> | null = null;
	#visibilityTimerId: ReturnType<typeof setTimeout> | null = null;
	#lastEventAt = 0;
	// Set whenever the stream goes down for a reason other than an auth restart.
	// Live events only carry server-side *changes*, so whatever moved while it was
	// down is missed; the next handshake refetches the pages to catch up.
	#needsCatchUp = false;
	// True while the stream is intentionally paused because the app is backgrounded.
	#pausedForVisibility = false;
	// Terminal flag set by destroy(); a destroyed client never reconnects.
	#destroyed = false;
	// One Sentry issue per outage, reset on the next successful handshake.
	#failureReported = false;
	#unsubscribeReachable: () => void;

	// Tracks registered listeners so they survive reconnects.
	// When EventSource reconnects, we re-attach all listeners to the new instance.
	// Each entry keeps the user handler (for identity on off()) and the JSON-parsing
	// wrapper actually attached to the EventSource.
	#listeners: Record<string, RegisteredListener[]> = {};

	constructor() {
		// Stop dialling while the browser reports no network; re-dial when it
		// comes back.
		window.addEventListener('offline', this.#handleOffline);
		window.addEventListener('online', this.#handleOnline);
		// Pause the stream while the app is backgrounded and resume on return;
		// Web Push keeps notifications flowing while it is down.
		document.addEventListener('visibilitychange', this.#handleVisibilityChange);
		// Skip the rest of a backoff wait once the backend is confirmed back.
		this.#unsubscribeReachable = onReachableChange(this.#handleReachableChange);
		this.#connect();
	}

	/**
	 * Subscribe to a named SSE event. The handler receives the parsed payload
	 * (typed per {@link SSEEventMap}). Survives reconnects automatically.
	 */
	on<K extends SSEEventName>(event: K, handler: SSEHandler<K>) {
		const handlers = this.#listeners[event] ?? (this.#listeners[event] = []);
		if (handlers.some((registered) => registered.handler === handler)) return;

		const wrapper: EventListener = (domEvent) => {
			const data = parseEventData(domEvent instanceof MessageEvent ? domEvent.data : undefined);
			(handler as (payload: unknown) => void)(data);
		};

		handlers.push({ handler, wrapper });
		this.#source?.addEventListener(event, wrapper);
	}

	/** Unsubscribe from a named SSE event. */
	off<K extends SSEEventName>(event: K, handler: SSEHandler<K>) {
		const handlers = this.#listeners[event];
		if (!handlers) return;

		const registered = handlers.find((entry) => entry.handler === handler);
		if (!registered) return;

		this.#source?.removeEventListener(event, registered.wrapper);
		const nextHandlers = handlers.filter((entry) => entry !== registered);

		// Clean up empty listener lists.
		if (nextHandlers.length === 0) {
			delete this.#listeners[event];
		} else {
			this.#listeners[event] = nextHandlers;
		}
	}

	/** Reconnect with a fresh session (after login/logout). */
	restart() {
		if (this.#destroyed) return;
		this.#closeSource();
		this.#reconnectAttempts = 0;
		this.#scheduleDial(RESTART_DEBOUNCE_MS);
	}

	/**
	 * Permanently tear down the client: close the stream and unhook the global
	 * window/document listeners registered in the constructor. Without this, a
	 * closed client would resurrect on the next `online` event. Call from the
	 * root layout's onDestroy; the client is unusable afterwards.
	 */
	destroy() {
		this.#destroyed = true;
		this.#closeSource();
		this.#clearDialTimer();
		this.#clearVisibilityTimer();
		window.removeEventListener('offline', this.#handleOffline);
		window.removeEventListener('online', this.#handleOnline);
		document.removeEventListener('visibilitychange', this.#handleVisibilityChange);
		this.#unsubscribeReachable();
	}

	#connect() {
		if (this.#destroyed || this.#source) return;
		this.#clearDialTimer();

		// Don't dial while the browser reports no network — the `online` event
		// resumes instead of a loop of failed attempts.
		if (!navigator.onLine) return;

		const source = new EventSource(`${PUBLIC_API_URL}/events`, { withCredentials: true });
		this.#source = source;
		this.#lastEventAt = Date.now();
		this.#armWatchdog(DIAL_TIMEOUT_MS, 'dial_timeout');

		// The attempt counter is reset on handshake, not here: a transport that
		// opens but never completes the handshake must still back off.
		source.onopen = () => {
			if (this.#source === source) this.#armWatchdog(HANDSHAKE_TIMEOUT_MS, 'handshake_timeout');
		};
		source.onerror = () => {
			if (this.#source === source) this.#dropAndRetry('transport_error');
		};

		source.addEventListener('connection_established', this.#handleHandshake);

		// Feed the liveness watchdog from every known event (incl. server pings),
		// so any traffic proves the stream alive — see ALL_SSE_EVENTS.
		for (const event of ALL_SSE_EVENTS) {
			source.addEventListener(event, this.#handleAnyEvent);
		}

		// Re-attach all registered listeners to the new EventSource instance.
		for (const [event, handlers] of Object.entries(this.#listeners)) {
			for (const { wrapper } of handlers) {
				source.addEventListener(event, wrapper);
			}
		}
	}

	// Stop now and dial again straight away, from a fresh backoff — the network or
	// the app's visibility just changed, so the old attempt count says nothing.
	#resume() {
		this.#closeSource();
		this.#needsCatchUp = true;
		this.#reconnectAttempts = 0;
		this.#connect();
	}

	// Go quiet until something resumes the stream.
	#suspend() {
		this.#closeSource();
		this.#clearDialTimer();
		this.#needsCatchUp = true;
	}

	#handleOffline = () => {
		this.#suspend();
	};

	// While backgrounded, the visibility resume handles the redial instead.
	#handleOnline = () => {
		if (!this.#pausedForVisibility) this.#resume();
	};

	// App backgrounded: after a grace window, drop the stream to stop radio churn.
	// The timer is left alone by offline/online flaps, which don't change how long
	// the app has been hidden — and visibilitychange won't fire again while hidden.
	#handleVisibilityChange = () => {
		if (document.visibilityState === 'hidden') {
			if (this.#pausedForVisibility || this.#visibilityTimerId) return;
			this.#visibilityTimerId = setTimeout(() => {
				this.#visibilityTimerId = null;
				this.#pausedForVisibility = true;
				this.#suspend();
			}, HIDDEN_PAUSE_GRACE_MS);
			return;
		}

		this.#clearVisibilityTimer();
		if (this.#pausedForVisibility) {
			this.#pausedForVisibility = false;
			this.#resume();
			return;
		}

		const silentForMs = Date.now() - this.#lastEventAt;
		if (this.#source && silentForMs > STALE_ON_RESUME_MS) this.#resume();
	};

	// The backend is confirmed reachable again (a probe, a load) while we sit out a
	// backoff wait — up to a minute by then. Good enough evidence to dial now.
	#handleReachableChange = () => {
		if (isReachable() && this.#dialTimerId !== null) this.#resume();
	};

	#handleHandshake = () => {
		// A live stream proves the backend is reachable — feed that to the probe.
		markReachable(true);
		this.#reconnectAttempts = 0;
		this.#failureReported = false;
		// Leave a trail for whatever error fires next; on a recovery it also closes
		// out the outage that #dropAndRetry may have filed as an issue.
		Sentry.addBreadcrumb({
			category: 'sse',
			level: 'info',
			message: this.#needsCatchUp ? 'SSE reconnected' : 'SSE connected'
		});

		// The first connect is skipped: the page's own load just fetched fresh data.
		// Shares the reconnect debounce with the reachability edge, so a recovery
		// that trips both refreshes once.
		if (this.#needsCatchUp) {
			this.#needsCatchUp = false;
			requestReconnectRefresh();
		}
	};

	// Resets the liveness watchdog; fires on every observed event (see #connect()).
	#handleAnyEvent = () => {
		this.#lastEventAt = Date.now();
		this.#armWatchdog(HEARTBEAT_TIMEOUT_MS, 'heartbeat_silence');
	};

	// Covers every way the stream can die without EventSource reporting it: a dial
	// that hangs before headers, a handshake that never comes, a silent transport.
	#armWatchdog(timeoutMs: number, reason: string) {
		this.#clearWatchdog();
		this.#watchdogId = setTimeout(() => {
			this.#watchdogId = null;
			console.warn(`SSE ${reason}, reconnecting...`);
			this.#dropAndRetry(reason);
		}, timeoutMs);
	}

	#dropAndRetry(reason: string) {
		this.#closeSource();
		this.#needsCatchUp = true;

		// Cheap trail (buffered, shipped only with the next captured event) so any
		// later error carries how the realtime stream was behaving on this device.
		Sentry.addBreadcrumb({
			category: 'sse',
			level: 'warning',
			message: `SSE dropped (${reason})`,
			data: { reason, attempts: this.#reconnectAttempts }
		});

		// A stream failure may mean the network died, not just an SSE hiccup. Probe
		// the health endpoint so reachability (and the offline banner) reflect reality
		// even when no `load` is running to report an outcome.
		void probeReachability();

		// Realtime silently dead for an attendee is worth one issue — on a saturated
		// venue network that is the failure we most need to hear about.
		if (this.#reconnectAttempts >= REPORT_AFTER_ATTEMPTS && !this.#failureReported) {
			this.#failureReported = true;
			Sentry.captureMessage('SSE stream failed after retries', {
				level: 'warning',
				tags: { sse_outcome: 'failed', sse_reason: reason },
				extra: { attempts: this.#reconnectAttempts }
			});
		}

		// Exponential backoff with full jitter: a random delay up to 1s, 2s, 4s,
		// ... capped. The randomness spreads re-dials out when a backend restart
		// drops every client at the same moment (thundering herd).
		const ceilingMs = Math.min(1000 * 2 ** this.#reconnectAttempts, MAX_RECONNECT_DELAY_MS);
		this.#reconnectAttempts++;
		this.#scheduleDial(Math.random() * ceilingMs);
	}

	#scheduleDial(delayMs: number) {
		this.#clearDialTimer();
		this.#dialTimerId = setTimeout(() => {
			this.#dialTimerId = null;
			this.#connect();
		}, delayMs);
	}

	#closeSource() {
		this.#clearWatchdog();
		if (!this.#source) return;
		this.#source.removeEventListener('connection_established', this.#handleHandshake);
		for (const event of ALL_SSE_EVENTS) {
			this.#source.removeEventListener(event, this.#handleAnyEvent);
		}
		this.#source.close();
		this.#source = null;
	}

	#clearDialTimer() {
		if (!this.#dialTimerId) return;
		clearTimeout(this.#dialTimerId);
		this.#dialTimerId = null;
	}

	#clearWatchdog() {
		if (!this.#watchdogId) return;
		clearTimeout(this.#watchdogId);
		this.#watchdogId = null;
	}

	#clearVisibilityTimer() {
		if (!this.#visibilityTimerId) return;
		clearTimeout(this.#visibilityTimerId);
		this.#visibilityTimerId = null;
	}
}

/** Create and set the EventsClient in Svelte context (call in root layout). */
export function setEventsClient(): EventsClient {
	const client = new EventsClient();
	setEvents(client);
	return client;
}

/**
 * Read the EventsClient from context. Deliberately lets `createContext`'s
 * missing-context error through: swallowing it turned a forgotten
 * `setEventsClient()` into realtime that silently never arrives.
 */
export function getEventsClient(): EventsClient {
	return getEvents();
}
