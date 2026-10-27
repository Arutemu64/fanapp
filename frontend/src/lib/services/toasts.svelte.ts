import { goto } from '$app/navigation';
import { createContext } from 'svelte';
import { toast } from 'svelte-sonner';
import { SvelteSet } from 'svelte/reactivity';

import type { NotificationDto } from '#lib/api/generated/index.js';

import { getApiErrorDetail } from '#lib/api/errors.js';
import { m } from '#lib/paraglide/messages.js';
import { toAppPath } from '#lib/utils/nav.js';
import { resolvePath } from '#lib/utils/paths.js';

type StatusToastType = 'success' | 'info' | 'warning' | 'error';

const [getToast, setToast] = createContext<ToastService>();

function htmlToPlainText(html: string): string {
	return new DOMParser().parseFromString(html, 'text/html').body.textContent;
}

class ToastService {
	readonly #seenPushIds = new SvelteSet<string>();

	add(message: string, type: StatusToastType = 'info') {
		const isProblem = type === 'error' || type === 'warning';
		const options = {
			id: `${type}:${message}`,
			duration: isProblem ? 5000 : 3000,
			closeButton: isProblem,
			position: 'bottom-center'
		} as const;
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

	error(err: unknown, fallback = m.toast_action_failed()) {
		this.add(getApiErrorDetail(err) ?? fallback, 'error');
	}

	push(notification: NotificationDto) {
		if (this.#seenPushIds.has(notification.id)) return;
		this.#seenPushIds.add(notification.id);

		const plainBody = notification.body ? htmlToPlainText(notification.body) : undefined;
		const path = notification.path ? toAppPath(notification.path) : undefined;

		toast(notification.title, {
			description: plainBody,
			descriptionClass: 'whitespace-pre-line',
			duration: 5000,
			closeButton: true,
			position: 'top-right',
			action:
				path !== undefined && path !== ''
					? {
							label: m.common_open(),
							onClick: () => {
								void goto(resolvePath(path));
							}
						}
					: undefined
		});
	}

	dismiss(id?: string | number) {
		if (id === undefined) {
			toast.dismiss();
		} else {
			toast.dismiss(id);
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
