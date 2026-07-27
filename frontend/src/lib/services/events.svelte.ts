import type { NotificationDTO } from '$lib/types/notifications';

import { browser } from '$app/environment';
import { invalidateAll } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import {
	isReachable,
	markReachable,
	onReachableChange,
	probeReachability
} from '$lib/services/reachability';
import { createContext } from 'svelte';

const [getEvents, setEvents] = createContext<EventsClient | null>();

/** Max reconnect attempts before giving up. */
const MAX_RECONNECT_ATTEMPTS = 10;
/** Wait briefly before reconnecting after auth changes to avoid flicker during navigation. */
const RESTART_DEBOUNCE_MS = 250;
/**
 * If the dial or the handshake stalls this long, treat the attempt as failed
 * and reconnect. Armed when dialing (a server that accepts the connection but
 * never responds would otherwise leave us in 'connecting' forever) and re-armed
 * once the transport opens to give the handshake its own window.
 */
const HANDSHAKE_TIMEOUT_MS = 5000;
/**
 * Reconnect when nothing arrives on the stream for this long. The backend emits
 * a named `ping` event after 30s of idle time (HEARTBEAT_INTERVAL_SECONDS in
 * backend/src/fanfan/presentation/web/routes/sse.py), so a healthy connection
 * always delivers *something* within that window. The browser cannot see the
 * transport die without a clean close (Wi-Fi roaming, NAT timeouts), so this
 * watchdog is the only thing that notices a silently dead stream. 3x the ping
 * interval tolerates slow networks and timer jitter.
 */
const HEARTBEAT_TIMEOUT_MS = 90000;
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
	#handshakeTimeoutId: ReturnType<typeof setTimeout> | null = null;
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
		if (browser) {
			window.addEventListener('offline', this.#handleOffline);
			window.addEventListener('online', this.#handleOnline);
			// Recover when connectivity returns after the stream gave up retrying.
			// While the reconnect loop is still running it handles recovery itself,
			// so we only step in once it has reached the terminal 'failed' state.
			this.#unsubscribeReachable = onReachableChange(this.#handleReachableChange);
			// Pause the stream while the app is backgrounded and resume on return;
			// Web Push keeps notifications flowing while it is down.
			document.addEventListener('visibilitychange', this.#handleVisibilityChange);
		}
		this.connect();
	}

	connect() {
		if (this.#destroyed || this.#source) return;

		this.#clearReconnectTimer();
		this.#clearRestartTimer();
		this.#clearHandshakeTimer();
		this.#clearHeartbeatTimer();
		this.#manualDisconnect = false;
		this.#handshake = null;

		// Don't dial while the browser reports no network — wait for the `online`
		// event instead of looping failed connection attempts.
		if (browser && !navigator.onLine) {
			this.#connectionStatus = 'disconnected';
			return;
		}

		this.#connectionStatus = 'connecting';

		this.#source = new EventSource(`${PUBLIC_API_URL}/events`, {
			withCredentials: true
		});

		// Covers a hung dial: a server (or proxy) that accepts the connection but
		// never sends headers fires neither onopen nor onerror for minutes, which
		// would leave the status stuck in 'connecting' with no retry scheduled.
		this.#armHandshakeTimeout();

		this.#source.onopen = () => {
			// The stream transport is open. We wait for the backend handshake
			// before calling the connection fully online. The attempt counter is
			// reset on handshake success, not here: a transport that opens but
			// never completes the handshake must still count toward `failed`,
			// otherwise it loops forever instead of surfacing the down banner.
			this.#connectionStatus = 'transport_open';
			this.#armHandshakeTimeout();
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
		if (handlers.some((registered) => registered.handler === handler)) return; // Already registered

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
		this.#clearHandshakeTimer();
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
		if (browser) {
			window.removeEventListener('offline', this.#handleOffline);
			window.removeEventListener('online', this.#handleOnline);
			document.removeEventListener('visibilitychange', this.#handleVisibilityChange);
		}
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
		this.#clearHandshakeTimer();
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
	// If the stream already exhausted its retries, its reconnect loop is no longer
	// running — restart it so the live stream returns without a manual refresh.
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

		this.#clearHandshakeTimer();
		this.#connectionStatus = 'connected';
		// A live stream proves the backend is reachable — feed that to the probe.
		markReachable(true);
		// Connection is fully online; reset backoff so the next blip starts fresh.
		this.#reconnectAttempts = 0;
	};

	#armHandshakeTimeout() {
		this.#clearHandshakeTimer();
		this.#handshakeTimeoutId = setTimeout(() => {
			console.warn('SSE handshake timed out, reconnecting...');
			this.#failAndReconnect();
		}, HANDSHAKE_TIMEOUT_MS);
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
		this.#clearHandshakeTimer();
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

	#clearHandshakeTimer() {
		if (!this.#handshakeTimeoutId) return;
		clearTimeout(this.#handshakeTimeoutId);
		this.#handshakeTimeoutId = null;
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
export function setEventsClient(): EventsClient | null {
	const client = browser ? new EventsClient() : null;
	setEvents(client);
	return client;
}

/**
 * Read the EventsClient from context. Null only when there is no browser (the
 * root layout stores null then). Deliberately lets `createContext`'s
 * missing-context error through: swallowing it turned a forgotten
 * `setEventsClient()` into realtime that silently never arrives.
 */
export function getEventsClient(): EventsClient | null {
	return getEvents();
}
