import type { Pathname } from '$app/types';
import type { NotificationDTO } from '$lib/types/notifications';

import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { getApiErrorDetail } from '$lib/api/errors';
import { createContext } from 'svelte';
import { toast } from 'svelte-sonner';
import { SvelteSet } from 'svelte/reactivity';

export type StatusToastType = 'success' | 'info' | 'warning' | 'error';

const [getToast, setToast] = createContext<ToastService>();

export class ToastService {
	#seenPushIds = new SvelteSet<string>();

	add(message: string, type: StatusToastType = 'info') {
		const duration = type === 'error' || type === 'warning' ? 5000 : 3000;
		// Action feedback sits at bottom-center, near where the user acted and
		// clear of the mobile bottom nav — distinct from push notifications, which
		// drop in top-right (see push()).
		const options = { duration, position: 'bottom-center' } as const;
		switch (type) {
			case 'success':
				toast.success(message, options);
				break;
			case 'error':
				toast.error(message, options);
				break;
			case 'warning':
				toast.warning(message, options);
				break;
			case 'info':
			default:
				toast.info(message, options);
				break;
		}
	}

	error(err: unknown) {
		let message = getApiErrorDetail(err) ?? 'Не удалось выполнить действие. Попробуй ещё раз.';

		if (typeof err === 'string') {
			message = err;
		} else if (err instanceof TypeError) {
			message = 'Не удалось связаться с сервером. Попробуй ещё раз.';
		}

		this.add(message, 'error');
	}

	push(notification: NotificationDTO) {
		if (this.#seenPushIds.has(notification.id)) return;
		this.#seenPushIds.add(notification.id);

		// Strip HTML tags if present so Sonner renders clean text
		const plainBody = notification.body ? notification.body.replace(/<[^>]*>/g, '') : undefined;

		toast(notification.title, {
			description: plainBody,
			duration: 5000,
			// Notifications drop in top-right, like an OS notification stack, clear
			// of the top bar — distinct from action feedback at bottom-center (add()).
			position: 'top-right',
			action: notification.path
				? {
						label: 'Открыть',
						onClick: () => {
							void goto(resolve(notification.path as Pathname));
						}
					}
				: undefined
		});
	}

	dismiss(id?: string | number) {
		if (id !== undefined) {
			toast.dismiss(id);
		} else {
			toast.dismiss();
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
