import type { NotificationDTO } from '$lib/types/notifications';

import { browser } from '$app/environment';
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
/** If the handshake never arrives, treat the stream as unhealthy and reconnect. */
const HANDSHAKE_TIMEOUT_MS = 5000;

export type ConnectionStatus =
	| 'disconnected'
	| 'connecting'
	| 'transport_open'
	| 'connected'
	| 'error'
	| 'failed';

export interface EventsHandshakePayload {
	server_time: string;
	authenticated: boolean;
	connection_id: string;
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
}

export type SSEEventName = keyof SSEEventMap;
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
	connectionStatus: ConnectionStatus = $state('disconnected');
	handshake: EventsHandshakePayload | null = $state(null);
	#source: EventSource | null = null;
	#reconnectAttempts = 0;
	#reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#handshakeTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#restartTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#manualDisconnect = false;

	// Tracks registered listeners so they survive reconnects.
	// When EventSource reconnects, we re-attach all listeners to the new instance.
	// Each entry keeps the user handler (for identity on off()) and the JSON-parsing
	// wrapper actually attached to the EventSource.
	#listeners: Record<string, RegisteredListener[]> = {};

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
			onReachableChange(this.#handleReachableChange);
		}
		this.connect();
	}

	connect() {
		if (this.#source) return;

		this.#clearReconnectTimer();
		this.#clearRestartTimer();
		this.#clearHandshakeTimer();
		this.#manualDisconnect = false;
		this.handshake = null;

		// Don't dial while the browser reports no network — wait for the `online`
		// event instead of looping failed connection attempts.
		if (browser && !navigator.onLine) {
			this.connectionStatus = 'disconnected';
			return;
		}

		this.connectionStatus = 'connecting';

		this.#source = new EventSource(`${PUBLIC_API_URL}/events`, {
			withCredentials: true
		});

		this.#source.onopen = () => {
			// The stream transport is open. We wait for the backend handshake
			// before calling the connection fully online. The attempt counter is
			// reset on handshake success, not here: a transport that opens but
			// never completes the handshake must still count toward `failed`,
			// otherwise it loops forever instead of surfacing the down banner.
			this.connectionStatus = 'transport_open';
			this.#armHandshakeTimeout();
		};

		this.#source.onerror = () => {
			if (this.#manualDisconnect) return;
			console.log('EventSource error, attempting to reconnect...');
			this.#failAndReconnect();
		};

		this.#source.addEventListener('connection_established', this.#handleHandshake);

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
		this.disconnect();
		this.connectionStatus = 'connecting';
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
		this.#closeSource();
		this.handshake = null;
		this.connectionStatus = 'disconnected';
		this.#reconnectAttempts = 0;
	}

	// Browser lost the network: stop reconnect attempts and go quiet. The offline
	// banner (OfflineService) covers the UI; SSE resumes on the `online` event.
	#handleOffline = () => {
		this.#manualDisconnect = true;
		this.#clearReconnectTimer();
		this.#clearRestartTimer();
		this.#clearHandshakeTimer();
		this.#closeSource();
		this.handshake = null;
		this.connectionStatus = 'disconnected';
	};

	// Network is back: re-dial from a clean slate.
	#handleOnline = () => {
		this.restart();
	};

	// Reachability recovered (e.g. the offline recovery poll or a load succeeded).
	// If the stream already exhausted its retries, its reconnect loop is no longer
	// running — restart it so the live stream returns without a manual refresh.
	#handleReachableChange = () => {
		if (this.connectionStatus === 'failed' && isReachable()) {
			this.restart();
		}
	};

	#handleHandshake = (event: Event) => {
		if (!(event instanceof MessageEvent)) return;

		try {
			this.handshake = JSON.parse(event.data) as EventsHandshakePayload;
		} catch (error) {
			console.warn('Failed to parse SSE handshake payload', error);
			this.handshake = null;
		}

		this.#clearHandshakeTimer();
		this.connectionStatus = 'connected';
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

	#failAndReconnect() {
		this.#clearHandshakeTimer();
		this.#closeSource();
		this.handshake = null;
		this.connectionStatus = 'error';

		// A stream failure may mean the network died, not just an SSE hiccup. Probe
		// the health endpoint so reachability (and the offline banner) reflect reality
		// even when no `load` is running to report an outcome.
		void probeReachability();

		if (this.#reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
			this.connectionStatus = 'failed';
			return;
		}

		// Exponential backoff: 1s, 2s, 4s, 8s, ... capped at 30s.
		const timeout = Math.min(1000 * 2 ** this.#reconnectAttempts, 30000);
		this.#reconnectTimeoutId = setTimeout(() => {
			this.#reconnectTimeoutId = null;
			this.connect();
		}, timeout);
		this.#reconnectAttempts++;
	}

	#closeSource() {
		if (!this.#source) return;
		this.#source.removeEventListener('connection_established', this.#handleHandshake);
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
}

/** Create and set the EventsClient in Svelte context (call in root layout). */
export function setEventsClient(): EventsClient | null {
	const client = browser ? new EventsClient() : null;
	setEvents(client);
	return client;
}

export function getEventsClient(): EventsClient | null {
	try {
		return getEvents();
	} catch {
		return null;
	}
}
