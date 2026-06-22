import { createContext } from 'svelte';
import { getApiErrorDetail } from '$lib/api/errors';
import type { NotificationDTO } from '$lib/types/notifications';

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
	notification?: NotificationDTO;
	timeoutId?: ReturnType<typeof setTimeout>;
}

const [getToast, setToast] = createContext<ToastService>();

export class ToastService {
	#toasts = $state<ToastItem[]>([]);
	readonly MAX_TOASTS = 3;

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

		if (typeof err === 'string') {
			message = err;
		}
		// Keep network and unexpected runtime errors user-friendly.
		else if (err instanceof Error) {
			message = 'Не удалось связаться с сервером. Попробуй ещё раз.';
		}

		this.add(message, 'error');
	}

	push(notification: NotificationDTO) {
		// Multiple components (navbar bell + notifications feed) listen to the same
		// SSE stream and each call push(). Skip if a toast for this notification is
		// already on screen so the user never sees it twice.
		const alreadyShown = this.#toasts.some(
			(toast) => toast.type === 'push' && toast.notification?.id === notification.id
		);
		if (alreadyShown) return;

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
