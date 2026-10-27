export function setAppBadgeCount(count: number): void {
	if (typeof navigator === 'undefined' || !('setAppBadge' in navigator)) return;
	void navigator.setAppBadge(count).catch(() => undefined);
}
