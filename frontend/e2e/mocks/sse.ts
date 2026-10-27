import type { BrowserContext, Page } from '@playwright/test';

export async function installSseDouble(context: BrowserContext): Promise<void> {
	await context.addInitScript(() => {
		const instances: EventTarget[] = [];

		class FakeEventSource extends EventTarget {
			static readonly CONNECTING = 0;
			static readonly OPEN = 1;
			static readonly CLOSED = 2;

			readonly url: string;
			readyState = FakeEventSource.CONNECTING;
			onopen: ((event: Event) => void) | null = null;
			onmessage: ((event: MessageEvent) => void) | null = null;
			onerror: ((event: Event) => void) | null = null;

			constructor(url: string | URL) {
				super();
				this.url = String(url);
				instances.push(this);
				queueMicrotask(() => {
					if (this.readyState === FakeEventSource.CLOSED) return;
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
				const index = instances.indexOf(this);
				if (index !== -1) instances.splice(index, 1);
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
	emit: (type: string, data: unknown) => void;
}

export async function emitSse(page: Page, type: string, data: unknown = {}): Promise<void> {
	await page.evaluate(
		([type, data]) => {
			const sse = (window as unknown as { __sse: SseHandle }).__sse;
			sse.emit(type, data);
		},
		[type, data] as const
	);
}
