import type { NotificationDTO } from '$lib/types/notifications';

import { DEFAULT_ACTION_FAILURE, getApiErrorDetail } from '$lib/api/errors';
import { createContext } from 'svelte';

export type ToastColor = 'green' | 'red' | 'yellow' | 'blue';

// Status toasts are feedback on the user's own action (success/error/…). Push
// toasts are inbound notifications from the SSE stream. They are different UX
// categories, so they live in separate queues with separate budgets — a burst
// of one can never evict the other — and render in separate screen regions
// (status at the bottom, push at the top). See ToastContainer.svelte.
export type StatusToastType = 'success' | 'info' | 'warning' | 'error';

export const StatusToastColors: Record<StatusToastType, ToastColor> = {
	success: 'green',
	info: 'blue',
	warning: 'yellow',
	error: 'red'
};

export interface StatusToastItem {
	id: number;
	message: string;
	type: StatusToastType;
	timeoutId?: ReturnType<typeof setTimeout>;
}

export interface PushToastItem {
	id: number;
	notification: NotificationDTO;
	timeoutId?: ReturnType<typeof setTimeout>;
}

const [getToast, setToast] = createContext<ToastService>();

export class ToastService {
	#statusToasts = $state<StatusToastItem[]>([]);
	#pushToasts = $state<PushToastItem[]>([]);
	// Monotonic id — Date.now() collides for two toasts added in the same tick,
	// which now matters because dismiss() spans both queues by id.
	#nextId = 0;
	readonly MAX_STATUS_TOASTS = 3;
	readonly MAX_PUSH_TOASTS = 2;

	get statusItems() {
		return this.#statusToasts;
	}

	get pushItems() {
		return this.#pushToasts;
	}

	add(message: string, type: StatusToastType = 'info') {
		const id = this.#nextId++;
		const newToast: StatusToastItem = { id, message, type };

		this.#statusToasts.unshift(newToast);
		this.#evict(this.#statusToasts, this.MAX_STATUS_TOASTS);

		const duration = type === 'error' || type === 'warning' ? 5000 : 3000;
		newToast.timeoutId = setTimeout(() => this.dismiss(id), duration);
	}

	error(err: unknown) {
		let message = getApiErrorDetail(err) ?? DEFAULT_ACTION_FAILURE;

		if (typeof err === 'string') {
			message = err;
		}
		// A failed fetch surfaces as a TypeError, so treat that as a connectivity
		// problem. Any other Error is an unexpected client-side bug, not a network
		// issue, so keep its message generic instead of blaming the server.
		else if (err instanceof TypeError) {
			message = 'Не удалось связаться с сервером. Попробуй ещё раз.';
		}

		this.add(message, 'error');
	}

	push(notification: NotificationDTO) {
		// Multiple components (navbar bell + notifications feed) listen to the same
		// SSE stream and each call push(). Skip if a toast for this notification is
		// already on screen so the user never sees it twice.
		const alreadyShown = this.#pushToasts.some(
			(toast) => toast.notification.id === notification.id
		);
		if (alreadyShown) return;

		const id = this.#nextId++;
		const newToast: PushToastItem = { id, notification };

		this.#pushToasts.unshift(newToast);
		this.#evict(this.#pushToasts, this.MAX_PUSH_TOASTS);

		newToast.timeoutId = setTimeout(() => this.dismiss(id), 5000);
	}

	dismiss(id: number) {
		const toast =
			this.#statusToasts.find((t) => t.id === id) ?? this.#pushToasts.find((t) => t.id === id);
		if (toast?.timeoutId) clearTimeout(toast.timeoutId);
		this.#statusToasts = this.#statusToasts.filter((t) => t.id !== id);
		this.#pushToasts = this.#pushToasts.filter((t) => t.id !== id);
	}

	// Drop the oldest toasts once a queue exceeds its budget, clearing their
	// pending auto-dismiss timers so they don't fire against a stale id.
	#evict(queue: (StatusToastItem | PushToastItem)[], max: number) {
		while (queue.length > max) {
			const popped = queue.pop();
			if (popped?.timeoutId) clearTimeout(popped.timeoutId);
		}
	}
}

export function setToastService() {
	const service = new ToastService();
	setToast(service);
	return service;
}

export function getToastService() {
	return getToast();
}
