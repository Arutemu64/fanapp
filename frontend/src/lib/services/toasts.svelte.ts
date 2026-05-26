import { createContext } from 'svelte';
import { getApiErrorDetail } from '$lib/api/errors';
import type { components } from '$lib/api/v1';

export type ToastColor = 'green' | 'red' | 'yellow' | 'blue' | 'gray';
export type ToastType = 'success' | 'info' | 'warning' | 'error' | 'push';

export const ToastTypeColors: Record<ToastType, ToastColor> = {
	success: 'green',
	info: 'blue',
	warning: 'yellow',
	error: 'red',
	push: 'gray'
};

export interface ToastItem {
	id: number;
	message: string;
	type: ToastType;
	notification?: components['schemas']['NotificationDTO'];
	timeoutId?: ReturnType<typeof setTimeout>;
}

const [getToast, setToast] = createContext<ToastService>();

export class ToastService {
	// Private state within the instance
	#toasts = $state<ToastItem[]>([]);
	readonly MAX_TOASTS = 3;

	// Getter to access the state reactively
	get items() {
		return this.#toasts;
	}

	add(message: string, type: ToastType = 'info') {
		const id = Date.now();
		const newToast: ToastItem = { id, message, type };

		this.#toasts.unshift(newToast);

		if (this.#toasts.length > this.MAX_TOASTS) {
			const popped = this.#toasts.pop();
			if (popped?.timeoutId) clearTimeout(popped.timeoutId);
		}

		const duration = type === 'error' || type === 'warning' ? 5000 : 3000;
		newToast.timeoutId = setTimeout(() => {
			this.dismiss(id);
		}, duration);
	}

	error(err: unknown) {
		let message = getApiErrorDetail(err) ?? 'Не удалось выполнить действие. Попробуй ещё раз.';

		// Handle string directly
		if (typeof err === 'string') {
			message = err;
		}
		// Keep network and unexpected runtime errors user-friendly.
		else if (err instanceof Error) {
			message = 'Не удалось связаться с сервером. Попробуй ещё раз.';
		}

		this.add(message, 'error');
	}

	push(notification: components['schemas']['NotificationDTO']) {
		const id = Date.now();
		const newToast: ToastItem = {
			id,
			message: notification.title,
			type: 'push',
			notification
		};

		this.#toasts.unshift(newToast);

		if (this.#toasts.length > this.MAX_TOASTS) {
			const popped = this.#toasts.pop();
			if (popped?.timeoutId) clearTimeout(popped.timeoutId);
		}

		newToast.timeoutId = setTimeout(() => {
			this.dismiss(id);
		}, 5000);
	}

	dismiss(id: number) {
		const toast = this.#toasts.find((t) => t.id === id);
		if (toast?.timeoutId) clearTimeout(toast.timeoutId);
		this.#toasts = this.#toasts.filter((t) => t.id !== id);
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
