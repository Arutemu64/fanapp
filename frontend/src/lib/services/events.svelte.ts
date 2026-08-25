import type { NotificationDTO } from '$lib/types/notifications';

import { invalidateAll } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import {
	isReachable,
	markReachable,
	onReachableChange,
	probeReachability
} from '$lib/services/reachability';
import { createContext } from 'svelte';

const [getEvents, setEvents] = createContext<EventsClient>();

/** Max reconnect attempts before backing off to the slow retry below. */
const MAX_RECONNECT_ATTEMPTS = 10;
/**
 * Once the fast retries are exhausted, keep dialing at this cadence rather than
 * stopping for good. A stream that stays broken while the backend is otherwise
 * healthy — a carrier proxy that kills long-lived connections, say — never
 * produces a reachability *transition*, so `markReachable(true)` notifies nobody
 * and none of the other recovery paths (`online`, reachability change, visibility
 * resume) ever fire. Without this the down banner would stick for the rest of the
 * session on an app whose pages all load fine. One dial a minute is cheap, and it
 * is paused with the rest of the stream while the app is backgrounded.
 */
const FAILED_RETRY_INTERVAL_MS = 60000;
/** Wait briefly before reconnecting after auth changes to avoid flicker during navigation. */
const RESTART_DEBOUNCE_MS = 250;
/**
 * If the dial stalls this long, treat the attempt as failed and reconnect. The
 * window covers DNS + TCP + TLS + response headers on a cold connection, which
 * on a congested venue cell is legitimately slow. It exists to catch a *hung*
 * dial — a server or proxy that accepts the connection but never sends headers,
 * firing neither onopen nor onerror for minutes — not a slow one, so it is set
 * well past plausible slowness: timing out a merely-slow network makes things
 * worse, since every retry restarts the whole dial and spends the fast-retry
 * budget on a connection that would have succeeded.
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
 * Pause the stream once the app has been backgrounded this long. Web Push covers
 * notifications while hidden, so holding SSE open only churns the mobile radio.
 * The grace window avoids thrashing on quick app-switches (following a link out
 * and straight back).
 */
const HIDDEN_PAUSE_GRACE_MS = 60000;

export type ConnectionStatus =
	'disconnected' | 'connecting' | 'transport_open' | 'connected' | 'error' | 'failed';

export interface EventsHandshakePayload {
	server_time: string;
	authenticated: boolean;
	connection_id: string;
}

// Broadcast whenever a vendor sync run changes state. Carries just enough to
// log or filter; subscribers refetch GET /sync/sources rather than trusting it
// as the source of truth, so a missed event self-heals on the next reconnect.
export interface SyncRunUpdatedPayload {
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
export interface SSEEventMap {
	connection_established: EventsHandshakePayload;
	schedule_updated: void;
	notification_created: NotificationDTO;
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
 * SSE (Server-Sent Events) client with automatic reconnection.
 *
 * Usage:
 *   const client = getEventsClient();
 *   client?.on('schedule_updated', handler);
 *   // cleanup:
 *   client?.off('schedule_updated', handler);
 */
export class EventsClient {
	#connectionStatus: ConnectionStatus = $state('disconnected');
	// Reassigned wholesale from parsed JSON, never mutated — `$state.raw` skips the
	// deep proxy `$state` would otherwise build for it.
	#handshake: EventsHandshakePayload | null = $state.raw(null);
	#source: EventSource | null = null;
	#reconnectAttempts = 0;
	#reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#stallTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#restartTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#visibilityTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#heartbeatTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#manualDisconnect = false;
	// True while the stream is intentionally paused because the app is backgrounded.
	#pausedForVisibility = false;
	// Terminal flag set by destroy(); a destroyed client never reconnects.
	#destroyed = false;
	#unsubscribeReachable: (() => void) | null = null;

	// Tracks registered listeners so they survive reconnects.
	// When EventSource reconnects, we re-attach all listeners to the new instance.
	// Each entry keeps the user handler (for identity on off()) and the JSON-parsing
	// wrapper actually attached to the EventSource.
	#listeners: Record<string, RegisteredListener[]> = {};

	/** Current stream state. Reactive — read it from a `$derived` or a template. */
	get connectionStatus(): ConnectionStatus {
		return this.#connectionStatus;
	}

	/** Payload of the last completed handshake; null whenever the stream is down. */
	get handshake(): EventsHandshakePayload | null {
		return this.#handshake;
	}

	constructor() {
		// React to OS network changes: pause the stream when the browser goes
		// offline (stops the reconnect churn and the "reconnecting" banner) and
		// re-dial when it comes back.
		window.addEventListener('offline', this.#handleOffline);
		window.addEventListener('online', this.#handleOnline);
		// Recover when connectivity returns after the stream gave up retrying.
		// While the reconnect loop is still running it handles recovery itself,
		// so we only step in once it has reached the terminal 'failed' state.
		this.#unsubscribeReachable = onReachableChange(this.#handleReachableChange);
		// Pause the stream while the app is backgrounded and resume on return;
		// Web Push keeps notifications flowing while it is down.
		document.addEventListener('visibilitychange', this.#handleVisibilityChange);
		this.connect();
	}

	connect() {
		if (this.#destroyed || this.#source) return;

		this.#clearReconnectTimer();
		this.#clearRestartTimer();
		this.#clearStallTimer();
		this.#clearHeartbeatTimer();
		this.#manualDisconnect = false;
		this.#handshake = null;

		// Don't dial while the browser reports no network — wait for the `online`
		// event instead of looping failed connection attempts.
		if (!navigator.onLine) {
			this.#connectionStatus = 'disconnected';
			return;
		}

		// A slow background retry from 'failed' must not downgrade the status to
		// 'connecting': the user has already been told the stream is down, and
		// flipping the banner off and back on every minute reads as flapping. Only
		// a transport that actually opens should change what they see.
		if (this.#connectionStatus !== 'failed') {
			this.#connectionStatus = 'connecting';
		}

		this.#source = new EventSource(`${PUBLIC_API_URL}/events`, {
			withCredentials: true
		});

		// Covers a hung dial: a server (or proxy) that accepts the connection but
		// never sends headers fires neither onopen nor onerror for minutes, which
		// would leave the status stuck in 'connecting' with no retry scheduled.
		this.#armStallTimeout(DIAL_TIMEOUT_MS, 'dial');

		this.#source.onopen = () => {
			// Mirrors connect()'s 'failed' guard above — see there for why; a
			// transport that opens and stalls on the handshake shouldn't blink
			// the banner off for HANDSHAKE_TIMEOUT_MS on every slow retry.
			//
			// The attempt counter is reset on handshake success, not here: a
			// transport that opens but never completes the handshake must still
			// count toward `failed`, or it loops forever instead of surfacing
			// the down banner.
			if (this.#connectionStatus !== 'failed') {
				this.#connectionStatus = 'transport_open';
			}
			this.#armStallTimeout(HANDSHAKE_TIMEOUT_MS, 'handshake');
		};

		this.#source.onerror = () => {
			if (this.#manualDisconnect) return;
			console.warn('EventSource error, attempting to reconnect...');
			this.#failAndReconnect();
		};

		this.#source.addEventListener('connection_established', this.#handleHandshake);

		// Feed the liveness watchdog from every known event (incl. server pings),
		// so any traffic proves the stream alive — see ALL_SSE_EVENTS.
		for (const event of ALL_SSE_EVENTS) {
			this.#source.addEventListener(event, this.#handleAnyEvent);
		}

		// Re-attach all registered listeners to the new EventSource instance.
		for (const [event, handlers] of Object.entries(this.#listeners)) {
			for (const { wrapper } of handlers) {
				this.#source.addEventListener(event, wrapper);
			}
		}
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

	/** Disconnect and immediately reconnect (e.g. after login/logout). */
	restart() {
		if (this.#destroyed) return;
		this.disconnect();
		this.#connectionStatus = 'connecting';
		this.#restartTimeoutId = setTimeout(() => {
			this.#restartTimeoutId = null;
			this.connect();
		}, RESTART_DEBOUNCE_MS);
	}

	/** Close the connection and stop reconnecting. */
	disconnect() {
		this.#manualDisconnect = true;
		this.#clearReconnectTimer();
		this.#clearRestartTimer();
		this.#clearStallTimer();
		this.#clearHeartbeatTimer();
		this.#clearVisibilityTimer();
		this.#closeSource();
		this.#handshake = null;
		this.#connectionStatus = 'disconnected';
		this.#reconnectAttempts = 0;
		this.#pausedForVisibility = false;
	}

	/**
	 * Permanently tear down the client: close the stream and unhook the global
	 * window/document listeners registered in the constructor. Without this, a
	 * disconnected client would resurrect on the next `online` event. Call from
	 * the root layout's onDestroy; the client is unusable afterwards.
	 */
	destroy() {
		this.disconnect();
		this.#destroyed = true;
		window.removeEventListener('offline', this.#handleOffline);
		window.removeEventListener('online', this.#handleOnline);
		document.removeEventListener('visibilitychange', this.#handleVisibilityChange);
		this.#unsubscribeReachable?.();
		this.#unsubscribeReachable = null;
	}

	// Browser lost the network: stop reconnect attempts and go quiet. The offline
	// banner (OfflineService) covers the UI; SSE resumes on the `online` event.
	#handleOffline = () => {
		this.#suspend();
	};

	// Tear down the live stream without the terminal semantics of disconnect():
	// keeps the backoff counter, ready to be resumed by an online/visibility event.
	// Deliberately leaves the visibility timer alone — it tracks how long the app
	// has been backgrounded, which a network blip does not change. Clearing it here
	// let an offline/online flap mid-background cancel the pending pause, so the
	// stream redialled and then stayed open on a hidden app until the user returned
	// (visibilitychange does not fire again while hidden), which is precisely the
	// radio churn HIDDEN_PAUSE_GRACE_MS exists to avoid.
	#suspend() {
		this.#manualDisconnect = true;
		this.#clearReconnectTimer();
		this.#clearRestartTimer();
		this.#clearStallTimer();
		this.#clearHeartbeatTimer();
		this.#closeSource();
		this.#handshake = null;
		this.#connectionStatus = 'disconnected';
	}

	// Network is back: re-dial from a clean slate — unless we're paused because the
	// app is backgrounded, in which case the visibility resume handles the redial.
	#handleOnline = () => {
		if (this.#pausedForVisibility) return;
		this.restart();
	};

	// App backgrounded: after a grace window, drop the stream to stop radio churn.
	// Foregrounding clears the pending timer and, if we did pause, redials and
	// refreshes the page to catch anything that changed while the stream was down.
	#handleVisibilityChange = () => {
		if (document.visibilityState === 'hidden') {
			if (this.#pausedForVisibility || this.#visibilityTimeoutId) return;
			this.#visibilityTimeoutId = setTimeout(() => {
				this.#visibilityTimeoutId = null;
				this.#pausedForVisibility = true;
				this.#suspend();
			}, HIDDEN_PAUSE_GRACE_MS);
			return;
		}

		this.#clearVisibilityTimer();
		if (this.#pausedForVisibility) {
			this.#pausedForVisibility = false;
			this.restart();
			// Live events only carry server-side *changes*; a full refresh catches
			// whatever updated while the stream was paused.
			void invalidateAll();
		}
	};

	// Reachability recovered (e.g. the offline recovery poll or a load succeeded).
	// A given-up stream is only retrying once a FAILED_RETRY_INTERVAL_MS by then;
	// a confirmed-reachable backend is good enough evidence to dial straight away
	// rather than sit out the rest of that minute. Note this fires on a reachability
	// *transition* only, which is exactly why the slow retry has to exist.
	#handleReachableChange = () => {
		if (this.#connectionStatus === 'failed' && isReachable()) {
			this.restart();
		}
	};

	#handleHandshake = (event: Event) => {
		if (!(event instanceof MessageEvent)) return;

		try {
			this.#handshake = JSON.parse(event.data as string) as EventsHandshakePayload;
		} catch (error) {
			console.warn('Failed to parse SSE handshake payload', error);
			this.#handshake = null;
		}

		this.#clearStallTimer();
		this.#connectionStatus = 'connected';
		// A live stream proves the backend is reachable — feed that to the probe.
		markReachable(true);
		// Connection is fully online; reset backoff so the next blip starts fresh.
		this.#reconnectAttempts = 0;
	};

	// Guards both stages of coming online — the dial, then the handshake. Either
	// stalling leaves the stream dead in a way EventSource itself never reports.
	#armStallTimeout(timeoutMs: number, stage: 'dial' | 'handshake') {
		this.#clearStallTimer();
		this.#stallTimeoutId = setTimeout(() => {
			console.warn(`SSE ${stage} timed out, reconnecting...`);
			this.#failAndReconnect();
		}, timeoutMs);
	}

	// Resets the liveness watchdog; fires on every observed event (see connect()).
	#handleAnyEvent = () => {
		this.#armHeartbeatTimeout();
	};

	#armHeartbeatTimeout() {
		this.#clearHeartbeatTimer();
		this.#heartbeatTimeoutId = setTimeout(() => {
			console.warn('SSE stream went silent, reconnecting...');
			this.#failAndReconnect();
		}, HEARTBEAT_TIMEOUT_MS);
	}

	#failAndReconnect() {
		this.#clearStallTimer();
		this.#clearHeartbeatTimer();
		this.#closeSource();
		this.#handshake = null;
		this.#connectionStatus = 'error';

		// A stream failure may mean the network died, not just an SSE hiccup. Probe
		// the health endpoint so reachability (and the offline banner) reflect reality
		// even when no `load` is running to report an outcome.
		void probeReachability();

		if (this.#reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
			this.#connectionStatus = 'failed';
			// Give up on *fast* recovery only — keep a slow dial going so the stream
			// self-heals without a manual refresh. See FAILED_RETRY_INTERVAL_MS for
			// why no other recovery path covers this. The counter stays maxed out, so
			// a failing retry lands back here rather than restarting the fast burst.
			this.#reconnectTimeoutId = setTimeout(() => {
				this.#reconnectTimeoutId = null;
				this.connect();
			}, FAILED_RETRY_INTERVAL_MS);
			return;
		}

		// Exponential backoff with full jitter: a random delay up to 1s, 2s, 4s,
		// ... capped at 30s. The randomness spreads re-dials out when a backend
		// restart drops every client at the same moment (thundering herd).
		const timeout = Math.random() * Math.min(1000 * 2 ** this.#reconnectAttempts, 30000);
		this.#reconnectTimeoutId = setTimeout(() => {
			this.#reconnectTimeoutId = null;
			this.connect();
		}, timeout);
		this.#reconnectAttempts++;
	}

	#closeSource() {
		if (!this.#source) return;
		this.#source.removeEventListener('connection_established', this.#handleHandshake);
		for (const event of ALL_SSE_EVENTS) {
			this.#source.removeEventListener(event, this.#handleAnyEvent);
		}
		this.#source.close();
		this.#source = null;
	}

	#clearReconnectTimer() {
		if (!this.#reconnectTimeoutId) return;
		clearTimeout(this.#reconnectTimeoutId);
		this.#reconnectTimeoutId = null;
	}

	#clearRestartTimer() {
		if (!this.#restartTimeoutId) return;
		clearTimeout(this.#restartTimeoutId);
		this.#restartTimeoutId = null;
	}

	#clearStallTimer() {
		if (!this.#stallTimeoutId) return;
		clearTimeout(this.#stallTimeoutId);
		this.#stallTimeoutId = null;
	}

	#clearVisibilityTimer() {
		if (!this.#visibilityTimeoutId) return;
		clearTimeout(this.#visibilityTimeoutId);
		this.#visibilityTimeoutId = null;
	}

	#clearHeartbeatTimer() {
		if (!this.#heartbeatTimeoutId) return;
		clearTimeout(this.#heartbeatTimeoutId);
		this.#heartbeatTimeoutId = null;
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
