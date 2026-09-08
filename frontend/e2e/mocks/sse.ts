import type { BrowserContext, Page } from '@playwright/test';

// The app opens `new EventSource('/api/events')` in events.svelte.ts for realtime
// updates. Playwright's route() can intercept that GET but cannot stream SSE
// frames back through it (microsoft/playwright#15353), so instead we replace the
// EventSource constructor before any app code runs. Two payoffs: unrelated tests
// get no live stream or reconnect timers to flake on, and a test can push a real
// named event (`schedule_updated`, a notification, …) via `emitSse()` and assert
// the UI reacts.
export async function installSseDouble(context: BrowserContext): Promise<void> {
	await context.addInitScript(() => {
		const instances: EventTarget[] = [];

		class FakeEventSource extends EventTarget {
			static readonly CONNECTING = 0;
			static readonly OPEN = 1;
			static readonly CLOSED = 2;

			readonly url: string;
			readyState = FakeEventSource.OPEN;
			onopen: ((event: Event) => void) | null = null;
			onmessage: ((event: MessageEvent) => void) | null = null;
			onerror: ((event: Event) => void) | null = null;

			constructor(url: string | URL) {
				super();
				this.url = String(url);
				instances.push(this);
				// Open on the next tick, then deliver the handshake the real backend
				// writes as the stream's first frame (`connection_established`). Without
				// it the client stays in `transport_open` and its liveness watchdog
				// would eventually reconnect — model a real, stable connection instead.
				queueMicrotask(() => {
					this.readyState = FakeEventSource.OPEN;
					this.onopen?.(new Event('open'));
					this.dispatchEvent(new Event('open'));
					const handshake = JSON.stringify({
						server_time: new Date().toISOString(),
						authenticated: false,
						connection_id: 'e2e-fake-connection'
					});
					this.dispatchEvent(new MessageEvent('connection_established', { data: handshake }));
				});
			}

			close(): void {
				this.readyState = FakeEventSource.CLOSED;
			}
		}

		Object.defineProperty(window, 'EventSource', { configurable: true, value: FakeEventSource });
		Object.defineProperty(window, '__sse', {
			configurable: true,
			value: {
				emit(type: string, data: unknown): void {
					const payload = typeof data === 'string' ? data : JSON.stringify(data);
					for (const target of instances) {
						target.dispatchEvent(new MessageEvent(type, { data: payload }));
					}
				}
			}
		});
	});
}

interface SseHandle {
	emit(type: string, data: unknown): void;
}

/** Emit a named SSE event into the running app (e.g. 'schedule_updated'). */
export async function emitSse(page: Page, type: string, data: unknown = {}): Promise<void> {
	await page.evaluate(
		([type, data]) => {
			const sse = (window as unknown as { __sse: SseHandle }).__sse;
			sse.emit(type as string, data);
		},
		[type, data] as const
	);
}
