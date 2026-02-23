import { browser } from '$app/environment';
import { PUBLIC_API_URL } from '$env/static/public';

class EventsClient {
	connectionStatus = $state('disconnected');
	source: EventSource | null = null;
	#reconnectAttempts = 0;

	constructor() {
		this.connect();
	}

	connect() {
		if (this.source) return; // Already connected

		this.connectionStatus = 'connecting';

		// Replace with your actual endpoint
		this.source = new EventSource(`${PUBLIC_API_URL}/events`);

		this.source.onopen = () => {
			this.connectionStatus = 'connected';
			this.#reconnectAttempts = 0;
		};

		this.source.onerror = () => {
			console.log('error');
			this.connectionStatus = 'error';
			// Basic reconnection logic
			this.source?.close();
			this.source = null;
			const timeout = Math.min(1000 * 2 ** this.#reconnectAttempts, 30000);
			setTimeout(() => this.connect(), timeout);
			this.#reconnectAttempts++;
		};
	}

	// Allow manual disconnect if needed (e.g., logout)
	disconnect() {
		if (this.source) {
			this.source.close();
			this.source = null;
			this.connectionStatus = 'disconnected';
		}
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
