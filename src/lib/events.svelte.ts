import { browser } from '$app/environment';
import { PUBLIC_API_URL } from '$env/static/public';

class EventsClient {
	connectionStatus = $state('disconnected');
	source: EventSource | null = null;
	#reconnectAttempts = 0;
	#reconnectTimeoutId: number | ReturnType<typeof setTimeout> | null = null; // Track timeout

	constructor() {
		this.connect();
	}

	connect() {
		if (this.source) return; // Already connected

		this.connectionStatus = 'connecting';

		// Make sure it sends cookies if API is on a different origin
		this.source = new EventSource(`${PUBLIC_API_URL}/events`, {
			withCredentials: true
		});

		this.source.onopen = () => {
			this.connectionStatus = 'connected';
			this.#reconnectAttempts = 0;
		};

		this.source.onerror = () => {
			console.log('EventSource error, attempting to reconnect...');
			this.connectionStatus = 'error';

			// Basic reconnection logic
			this.source?.close();
			this.source = null;

			const timeout = Math.min(1000 * 2 ** this.#reconnectAttempts, 30000);
			// Save timeout ID so we can cancel it if disconnect() is called
			this.#reconnectTimeoutId = setTimeout(() => this.connect(), timeout);
			this.#reconnectAttempts++;
		};
	}

	restart() {
		this.disconnect();
		this.connect();
	}

	// Allow manual disconnect if needed (e.g., logout)
	disconnect() {
		// Clear any pending reconnections to prevent leaks
		if (this.#reconnectTimeoutId) {
			clearTimeout(this.#reconnectTimeoutId);
			this.#reconnectTimeoutId = null;
		}

		if (this.source) {
			this.source.close();
			this.source = null;
		}

		this.connectionStatus = 'disconnected';
		this.#reconnectAttempts = 0; // Reset attempts for the next connection
	}
}

// Lazy singleton - only created when first accessed in the browser
let _instance: EventsClient | null = null;

export function getEventsClient(): EventsClient | null {
	if (!browser) {
		return null;
	}
	if (!_instance) {
		_instance = new EventsClient();
	}
	return _instance;
}
