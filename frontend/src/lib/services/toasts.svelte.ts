import { setContext, getContext } from 'svelte';
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
}

const TOAST_CTX_KEY = Symbol('TOAST_CTX');

export class ToastService {
	// Private state within the instance
	#toasts = $state<ToastItem[]>([]);

	// Getter to access the state reactively
	get items() {
		return this.#toasts;
	}

	add(message: string, type: ToastType = 'info') {
		const id = Date.now();
		const newToast: ToastItem = { id, message, type };

		this.#toasts.push(newToast);

		// Auto-dismiss after 5 seconds
		setTimeout(() => {
			this.dismiss(id);
		}, 5000);
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

		this.#toasts.push(newToast);

		// Auto-dismiss after 5 seconds
		setTimeout(() => {
			this.dismiss(id);
		}, 5000);
	}

	dismiss(id: number) {
		this.#toasts = this.#toasts.filter((t) => t.id !== id);
	}
}

export function setToastService() {
	const service = new ToastService();
	return setContext(TOAST_CTX_KEY, service);
}

export function getToastService() {
	return getContext<ToastService>(TOAST_CTX_KEY);
}
