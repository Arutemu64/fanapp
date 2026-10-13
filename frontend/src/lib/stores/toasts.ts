import { defineStore } from 'pinia';
import { useRouter } from 'vue-router';
import { toast } from 'vue-sonner';

import type { NotificationDto } from '#lib/api/generated/index.js';

import { getApiErrorDetail } from '#lib/api/errors.js';

export type StatusToastType = 'success' | 'info' | 'warning' | 'error';

// A regex tag strip would leave entities escaped by the backend sanitizer
// (`&amp;`, `&lt;`) on screen; the parser decodes them. DOMParser never runs
// scripts or loads resources from the parsed document.
function htmlToPlainText(html: string): string {
	return new DOMParser().parseFromString(html, 'text/html').body.textContent ?? '';
}

/**
 * Toast notifications. A Pinia store rather than a module singleton because it
 * holds the dedupe set of already-shown pushes, which must not survive a
 * login/logout (the store is torn down with the app's Pinia instance).
 *
 * `useRouter()` is an `inject()`, so it works in this setup function only
 * while Vue can resolve app-level provides: Pinia runs setup stores inside the
 * app's context, so the first `useToastStore()` from a component, a router
 * guard or a query callback is fine once the app has been mounted with both
 * plugins installed. Outside an app (unit tests), `router` is undefined and
 * the «Открыть» action simply does nothing.
 */
export const useToastStore = defineStore('toasts', () => {
	const router = useRouter() as ReturnType<typeof useRouter> | undefined;
	const seenPushIds = new Set<string>();

	function add(message: string, type: StatusToastType = 'info') {
		const isProblem = type === 'error' || type === 'warning';
		const options = {
			// Same type + text reuses the toast, so a repeated failure refreshes the
			// one on screen instead of stacking duplicates.
			id: `${type}:${message}`,
			duration: isProblem ? 5000 : 3000,
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
	function error(err: unknown, fallback = 'Не удалось выполнить действие. Попробуй ещё раз.') {
		add(getApiErrorDetail(err) ?? fallback, 'error');
	}

	function push(notification: NotificationDto) {
		if (seenPushIds.has(notification.id)) return;
		seenPushIds.add(notification.id);

		// Sonner's description is plain text, not HTML.
		const plainBody = notification.body ? htmlToPlainText(notification.body) : undefined;
		const path = notification.path;

		toast(notification.title, {
			description: plainBody,
			// The body keeps its line breaks as "\n" (see HtmlSanitizer).
			descriptionClass: 'whitespace-pre-line',
			duration: 5000,
			// Swipe is the only other way to clear it early, and WCAG 2.5.7 wants a
			// tap alternative to every drag gesture.
			closeButton: true,
			// Notifications drop in top-right, like an OS notification stack, clear
			// of the top bar — distinct from action feedback at bottom-center (add()).
			position: 'top-right',
			action: path
				? {
						label: 'Открыть',
						onClick: () => {
							void router?.push(path);
						}
					}
				: undefined
		});
	}

	function dismiss(id?: string | number) {
		if (id !== undefined) {
			toast.dismiss(id);
		} else {
			toast.dismiss();
		}
	}

	return { add, error, push, dismiss };
});
