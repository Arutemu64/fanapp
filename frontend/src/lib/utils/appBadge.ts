/**
 * Badging API helper: mirrors the unread-notification count onto the installed
 * app's icon. Supported on iOS/iPadOS 16.4+ home-screen web apps (needs the
 * notification permission our push subscribers already granted) and on
 * Chrome/Edge-installed desktop PWAs. Android Chrome lacks the API but shows
 * its own notification dot from push, so every platform ends up covered.
 *
 * `setAppBadge(0)` clears the badge, so this single entry point handles both
 * setting and clearing. Badging is best-effort decoration: it no-ops where the
 * API is missing and swallows rejections (e.g. permission not granted).
 */
export function setAppBadgeCount(count: number): void {
	if (typeof navigator === 'undefined' || !('setAppBadge' in navigator)) return;
	void navigator.setAppBadge(count).catch(() => undefined);
}
