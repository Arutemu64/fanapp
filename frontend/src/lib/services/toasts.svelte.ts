import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { createContext } from 'svelte';
import { toast } from 'svelte-sonner';
import { SvelteSet } from 'svelte/reactivity';

import type { NotificationDto } from '#lib/api/generated/index.js';

import { getApiErrorDetail } from '#lib/api/errors.js';
import { toAppPath } from '#lib/utils/nav.js';

export type StatusToastType = 'success' | 'info' | 'warning' | 'error';

const [getToast, setToast] = createContext<ToastService>();

// A floor plus about a second per 120 characters, so longer copy stays up long
// enough to read — the reading-time heuristic from
// https://github.com/adobe/react-spectrum/pull/29 and
// https://design.sis.gov.uk/components/toast
function statusToastDuration(message: string, isProblem: boolean): number {
	const floor = isProblem ? 5000 : 3000;
	const readingTime = Math.ceil(message.length / 120) * 1000;
	return floor + readingTime;
}

// A regex tag strip would leave entities escaped by the backend sanitizer
// (`&amp;`, `&lt;`) on screen; the parser decodes them. DOMParser never runs
// scripts or loads resources from the parsed document.
function htmlToPlainText(html: string): string {
	return new DOMParser().parseFromString(html, 'text/html').body.textContent ?? '';
}

export class ToastService {
	#seenPushIds = new SvelteSet<string>();

	add(message: string, type: StatusToastType = 'info') {
		const isProblem = type === 'error' || type === 'warning';
		const options = {
			// Same type + text reuses the toast, so a repeated failure refreshes the
			// one on screen instead of stacking duplicates.
			id: `${type}:${message}`,
			duration: statusToastDuration(message, isProblem),
			// An error exists only in this toast (nowhere else to re-read it), so it
			// gets an explicit dismiss control on top of the longer timer:
			// https://ux.redhat.com/patterns/alert/accessibility/
			closeButton: isProblem,
			// Action feedback sits at bottom-center, near where the user acted and
			// clear of the mobile bottom nav — distinct from push notifications, which
			// drop in top-right (see push()).
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

	// Takes the SDK's `error` as-is. A non-JSON error body (a proxy's HTML 502
	// page) arrives as a plain string, so a string is never shown verbatim — use
	// add(message, 'error') for copy you wrote yourself.
	error(err: unknown, fallback = 'Не удалось выполнить действие. Попробуй ещё раз.') {
		this.add(getApiErrorDetail(err) ?? fallback, 'error');
	}

	push(notification: NotificationDto) {
		if (this.#seenPushIds.has(notification.id)) return;
		this.#seenPushIds.add(notification.id);

		// Sonner's description is plain text, not HTML.
		const plainBody = notification.body ? htmlToPlainText(notification.body) : undefined;
		const path = notification.path ? toAppPath(notification.path) : undefined;

		toast(notification.title, {
			description: plainBody,
			// The body keeps its line breaks as "\n" (see HtmlSanitizer).
			descriptionClass: 'whitespace-pre-line',
			duration: 5000,
			// Notifications drop in top-right, like an OS notification stack, clear
			// of the top bar — distinct from action feedback at bottom-center (add()).
			position: 'top-right',
			action: path
				? {
						label: 'Открыть',
						onClick: () => {
							void goto(resolve(path));
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
