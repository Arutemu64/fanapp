import { getContext, setContext } from 'svelte';
import { browser } from '$app/environment';
import { PUBLIC_API_URL } from '$env/static/public';

const EVENTS_CLIENT_KEY = Symbol('EVENTS_CLIENT');

/** Max reconnect attempts before giving up. */
const MAX_RECONNECT_ATTEMPTS = 10;

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error' | 'failed';

/**
 * SSE (Server-Sent Events) client with automatic reconnection.
 *
 * Usage:
 *   const client = getEventsClient();
 *   client?.on('update_schedule', handler);
 *   // cleanup:
 *   client?.off('update_schedule', handler);
 */
export class EventsClient {
	connectionStatus: ConnectionStatus = $state('disconnected');
	#source: EventSource | null = null;
	#reconnectAttempts = 0;
	#reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;

	// Tracks registered listeners so they survive reconnects.
	// When EventSource reconnects, we re-attach all listeners to the new instance.
	#listeners: Map<string, Set<EventListener>> = new Map();

	constructor() {
		this.connect();
	}

	connect() {
		if (this.#source) return;

		this.connectionStatus = 'connecting';

		this.#source = new EventSource(`${PUBLIC_API_URL}/events`, {
			withCredentials: true
		});

		this.#source.onopen = () => {
			this.connectionStatus = 'connected';
			this.#reconnectAttempts = 0;
		};

		this.#source.onerror = () => {
			console.log('EventSource error, attempting to reconnect...');
			this.connectionStatus = 'error';

			this.#source?.close();
			this.#source = null;

			if (this.#reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
				this.connectionStatus = 'failed';
				return;
			}

			// Exponential backoff: 1s, 2s, 4s, 8s, ... capped at 30s.
			const timeout = Math.min(1000 * 2 ** this.#reconnectAttempts, 30000);
			this.#reconnectTimeoutId = setTimeout(() => this.connect(), timeout);
			this.#reconnectAttempts++;
		};

		// Re-attach all registered listeners to the new EventSource instance.
		for (const [event, handlers] of this.#listeners) {
			for (const handler of handlers) {
				this.#source.addEventListener(event, handler);
			}
		}
	}

	/** Subscribe to a named SSE event. Survives reconnects automatically. */
	on(event: string, handler: EventListener) {
		if (!this.#listeners.has(event)) {
			this.#listeners.set(event, new Set());
		}

		const handlers = this.#listeners.get(event)!;
		if (handlers.has(handler)) return; // Already registered

		handlers.add(handler);
		this.#source?.addEventListener(event, handler);
	}

	/** Unsubscribe from a named SSE event. */
	off(event: string, handler: EventListener) {
		const handlers = this.#listeners.get(event);
		if (!handlers?.has(handler)) return;

		handlers.delete(handler);
		this.#source?.removeEventListener(event, handler);

		// Clean up empty sets.
		if (handlers.size === 0) {
			this.#listeners.delete(event);
		}
	}

	/** Disconnect and immediately reconnect (e.g. after login/logout). */
	restart() {
		this.disconnect();
		this.connect();
	}

	/** Close the connection and stop reconnecting. */
	disconnect() {
		if (this.#reconnectTimeoutId) {
			clearTimeout(this.#reconnectTimeoutId);
			this.#reconnectTimeoutId = null;
		}

		if (this.#source) {
			this.#source.close();
			this.#source = null;
		}

		this.connectionStatus = 'disconnected';
		this.#reconnectAttempts = 0;
	}
}

/** Create and set the EventsClient in Svelte context (call in root layout). */
export function setEventsClient(): EventsClient | null {
	const client = browser ? new EventsClient() : null;
	setContext(EVENTS_CLIENT_KEY, client);
	return client;
}

/** Retrieve the EventsClient from Svelte context. */
export function getEventsClient(): EventsClient | null {
	return getContext<EventsClient | null>(EVENTS_CLIENT_KEY) ?? null;
}
