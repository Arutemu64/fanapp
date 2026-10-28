import type { QueryClient } from '@tanstack/svelte-query';

import { PUBLIC_API_URL } from '$app/env/public';
import * as Sentry from '@sentry/sveltekit';
import { createContext } from 'svelte';

import type { NotificationDto, SseEventName } from '#lib/api/generated/index.js';

import {
	isReachable,
	markReachable,
	onReachableChange,
	probeReachability
} from '#lib/services/reachability.js';

const [getEvents, setEvents] = createContext<EventsClient>();

const MAX_RECONNECT_DELAY_MS = 60000;
const REPORT_AFTER_ATTEMPTS = 10;
const RESTART_DEBOUNCE_MS = 250;
const DIAL_TIMEOUT_MS = 15000;
const HANDSHAKE_TIMEOUT_MS = 5000;
const HEARTBEAT_TIMEOUT_MS = 45000;
const STALE_ON_RESUME_MS = 30000;
const HIDDEN_PAUSE_GRACE_MS = 60000;

interface EventsHandshakePayload {
	server_time: string;
	authenticated: boolean;
	connection_id: string;
}

interface SyncRunUpdatedPayload {
	source: string;
	status: string;
}

// Keys must equal the generated SseEventName union: a new backend event fails
// here until it has a payload type, and a removed one fails as an extra key.
type EventPayloads<
	T extends Record<SseEventName, unknown> & Record<Exclude<keyof T, SseEventName>, never>
> = T;

type SSEEventMap = EventPayloads<{
	connection_established: EventsHandshakePayload;
	schedule_updated: undefined;
	notification_created: NotificationDto;
	sync_run_updated: SyncRunUpdatedPayload;
	config_updated: undefined;
	ping: undefined;
}>;

export type SSEEventName = SseEventName;

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

function parseEventData(raw: unknown): unknown {
	if (typeof raw !== 'string' || raw.length === 0) return undefined;
	try {
		return JSON.parse(raw);
	} catch {
		console.warn('SSE event payload is not valid JSON', raw);
		return raw;
	}
}

export class EventsClient {
	#source: EventSource | null = null;
	#reconnectAttempts = 0;
	#dialTimerId: ReturnType<typeof setTimeout> | null = null;
	#watchdogId: ReturnType<typeof setTimeout> | null = null;
	#visibilityTimerId: ReturnType<typeof setTimeout> | null = null;
	#lastEventAt = 0;
	#needsCatchUp = false;
	readonly #queryClient: QueryClient;
	#pausedForVisibility = false;
	#destroyed = false;
	#failureReported = false;
	readonly #unsubscribeReachable: () => void;

	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- listener bookkeeping, never rendered
	readonly #listeners = new Map<string, RegisteredListener[]>();

	constructor(queryClient: QueryClient) {
		this.#queryClient = queryClient;
		window.addEventListener('offline', this.#handleOffline);
		window.addEventListener('online', this.#handleOnline);
		document.addEventListener('visibilitychange', this.#handleVisibilityChange);
		this.#unsubscribeReachable = onReachableChange(this.#handleReachableChange);
		this.#connect();
	}

	on<K extends SSEEventName>(event: K, handler: SSEHandler<K>) {
		let handlers = this.#listeners.get(event);
		if (!handlers) {
			handlers = [];
			this.#listeners.set(event, handlers);
		}
		if (handlers.some((registered) => registered.handler === handler)) return;

		const wrapper: EventListener = (domEvent) => {
			const data = parseEventData(domEvent instanceof MessageEvent ? domEvent.data : undefined);
			(handler as (payload: unknown) => void)(data);
		};

		handlers.push({ handler, wrapper });
		this.#source?.addEventListener(event, wrapper);
	}

	off<K extends SSEEventName>(event: K, handler: SSEHandler<K>) {
		const handlers = this.#listeners.get(event);
		if (!handlers) return;

		const registered = handlers.find((entry) => entry.handler === handler);
		if (!registered) return;

		this.#source?.removeEventListener(event, registered.wrapper);
		const nextHandlers = handlers.filter((entry) => entry !== registered);

		if (nextHandlers.length === 0) {
			this.#listeners.delete(event);
		} else {
			this.#listeners.set(event, nextHandlers);
		}
	}

	restart() {
		if (this.#destroyed) return;
		this.#closeSource();
		this.#reconnectAttempts = 0;
		this.#scheduleDial(RESTART_DEBOUNCE_MS);
	}

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

		if (!navigator.onLine) return;

		const source = new EventSource(`${PUBLIC_API_URL}/events`, { withCredentials: true });
		this.#source = source;
		this.#lastEventAt = Date.now();
		this.#armWatchdog(DIAL_TIMEOUT_MS, 'dial_timeout');

		source.onopen = () => {
			if (this.#source === source) this.#armWatchdog(HANDSHAKE_TIMEOUT_MS, 'handshake_timeout');
		};
		source.onerror = () => {
			if (this.#source === source) this.#dropAndRetry('transport_error');
		};

		source.addEventListener('connection_established', this.#handleHandshake);

		for (const event of ALL_SSE_EVENTS) {
			source.addEventListener(event, this.#handleAnyEvent);
		}

		for (const [event, handlers] of this.#listeners) {
			for (const { wrapper } of handlers) {
				source.addEventListener(event, wrapper);
			}
		}
	}

	#resume() {
		this.#closeSource();
		this.#needsCatchUp = true;
		this.#reconnectAttempts = 0;
		this.#connect();
	}

	#suspend() {
		this.#closeSource();
		this.#clearDialTimer();
		this.#needsCatchUp = true;
	}

	readonly #handleOffline = () => {
		this.#suspend();
	};

	readonly #handleOnline = () => {
		if (!this.#pausedForVisibility) this.#resume();
	};

	readonly #handleVisibilityChange = () => {
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
			this.#needsCatchUp = false;
			return;
		}

		const silentForMs = Date.now() - this.#lastEventAt;
		if (this.#source && silentForMs > STALE_ON_RESUME_MS) this.#resume();
	};

	readonly #handleReachableChange = () => {
		if (isReachable() && this.#dialTimerId !== null) this.#resume();
	};

	readonly #handleHandshake = () => {
		markReachable(true);
		this.#reconnectAttempts = 0;
		this.#failureReported = false;
		Sentry.addBreadcrumb({
			category: 'sse',
			level: 'info',
			message: this.#needsCatchUp ? 'SSE reconnected' : 'SSE connected'
		});

		if (this.#needsCatchUp) {
			this.#needsCatchUp = false;
			void this.#queryClient.invalidateQueries();
		}
	};

	readonly #handleAnyEvent = () => {
		this.#lastEventAt = Date.now();
		this.#armWatchdog(HEARTBEAT_TIMEOUT_MS, 'heartbeat_silence');
	};

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

		Sentry.addBreadcrumb({
			category: 'sse',
			level: 'warning',
			message: `SSE dropped (${reason})`,
			data: { reason, attempts: this.#reconnectAttempts }
		});

		void probeReachability();

		if (this.#reconnectAttempts >= REPORT_AFTER_ATTEMPTS && !this.#failureReported) {
			this.#failureReported = true;
			Sentry.captureMessage('SSE stream failed after retries', {
				level: 'warning',
				tags: { sse_outcome: 'failed', sse_reason: reason },
				extra: { attempts: this.#reconnectAttempts }
			});
		}

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

export function setEventsClient(queryClient: QueryClient): EventsClient {
	const client = new EventsClient(queryClient);
	setEvents(client);
	return client;
}

export function getEventsClient(): EventsClient {
	return getEvents();
}
