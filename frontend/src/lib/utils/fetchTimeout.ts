export function timeoutSignal(ms: number): AbortSignal {
	if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
		return AbortSignal.timeout(ms);
	}

	const controller = new AbortController();
	setTimeout(() => controller.abort(new DOMException('signal timed out', 'TimeoutError')), ms);
	return controller.signal;
}

export function anySignal(signals: AbortSignal[]): AbortSignal {
	if (typeof AbortSignal.any === 'function') {
		return AbortSignal.any(signals);
	}

	const controller = new AbortController();
	for (const signal of signals) {
		if (signal.aborted) {
			controller.abort(signal.reason);
			break;
		}
		signal.addEventListener('abort', () => controller.abort(signal.reason), { once: true });
	}
	return controller.signal;
}

export const FIRST_PAINT_TIMEOUT_MS = 3500;
