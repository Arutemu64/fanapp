import { getContext, setContext } from 'svelte';
import { browser } from '$app/environment';
import { PUBLIC_API_URL } from '$env/static/public';

const EVENTS_CLIENT_KEY = Symbol('EVENTS_CLIENT');

const MAX_RECONNECT_ATTEMPTS = 10;

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error' | 'failed';

export class EventsClient {
	connectionStatus: ConnectionStatus = $state('disconnected');
	#source: EventSource | null = null;
	#reconnectAttempts = 0;
	#reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
	#listeners: Map<string, Map<EventListener, EventListener>> = new Map();

	constructor() {
		this.connect();
	}

	connect() {
		if (this.#source) return; // Already connected

		this.connectionStatus = 'connecting';

		this.#source = new EventSource(`${PUBLIC_API_URL}/events`, {
			withCredentials: true
		});

		this.#source.onopen = (event) => {
			this.connectionStatus = 'connected';
			this.#reconnectAttempts = 0;
		};

		this.#source.onerror = (event) => {
			console.log('EventSource error, attempting to reconnect...');
			this.connectionStatus = 'error';

			this.#source?.close();
			this.#source = null;

			if (this.#reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
				this.connectionStatus = 'failed';
				return;
			}

			const timeout = Math.min(1000 * 2 ** this.#reconnectAttempts, 30000);
			this.#reconnectTimeoutId = setTimeout(() => this.connect(), timeout);
			this.#reconnectAttempts++;
		};

		// Re-attach all registered listeners to the new source
		for (const [event, handlers] of this.#listeners) {
			for (const wrappedHandler of handlers.values()) {
				this.#source.addEventListener(event, wrappedHandler);
			}
		}
	}

	on(event: string, handler: EventListener) {
		if (!this.#listeners.has(event)) {
			this.#listeners.set(event, new Map());
		}

		const handlers = this.#listeners.get(event)!;
		if (handlers.has(handler)) return;

		handlers.set(handler, handler);
		this.#source?.addEventListener(event, handler);
	}

	off(event: string, handler: EventListener) {
		const handlers = this.#listeners.get(event);
		const wrappedHandler = handlers?.get(handler);
		if (!wrappedHandler) return;

		handlers?.delete(handler);
		this.#source?.removeEventListener(event, wrappedHandler);

		if (handlers && handlers.size === 0) {
			this.#listeners.delete(event);
		}
	}

	restart() {
		this.disconnect();
		this.connect();
	}

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

export function setEventsClient(): EventsClient | null {
	let client: EventsClient | null = null;
	if (browser) {
		client = new EventsClient();
	}
	setContext(EVENTS_CLIENT_KEY, client);
	return client;
}

export function getEventsClient(): EventsClient | null {
	return getContext<EventsClient | null>(EVENTS_CLIENT_KEY) ?? null;
}
