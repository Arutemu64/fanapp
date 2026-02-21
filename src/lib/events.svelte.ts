import { browser } from '$app/environment';

class EventsClient {
	connectionStatus = $state('disconnected');
	source: EventSource | null = null;
	#reconnectAttempts = 0;

	constructor() {
		// Auto-connect when the store is initialized in the browser
		if (browser) {
			this.connect();
		}
	}

	connect() {
		if (this.source) return; // Already connected

		this.connectionStatus = 'connecting';

		// Replace with your actual endpoint
		this.source = new EventSource('http://192.168.1.50:8081/api/events');

		this.source.onopen = () => {
			this.connectionStatus = 'connected';
			this.#reconnectAttempts = 0;
		};

		this.source.onerror = () => {
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

// Export a singleton instance
export const eventsClient = new EventsClient();
