import { m } from '#lib/paraglide/messages.js';
import { reachability } from '#lib/services/reachability.js';
import { getToastService } from '#lib/services/toasts.svelte.js';

/**
 * Gate for write controls that must stay online-only (ADR-0022) on pages that
 * remain usable offline: the cached content is worth showing, but the mutations
 * on top of it would fail.
 *
 * Offline the control is dimmed with `aria-disabled` rather than `disabled`, and
 * a tap explains itself with a toast instead of acting. Native `disabled` can't be
 * focused and swallows the tap, and its `title` hint never shows on a touch
 * screen, so the user is left guessing why it's dead
 * (https://smart-interface-design-patterns.com/articles/disabled-buttons/).
 *
 * Call during component init (it reads the toast context). A control opts in
 * with one pair: `aria-disabled={gate.blocked}` and `onclick={gate.guard(handler)}`
 * (or `onsubmit`, `onCheckedChange`). Whole-surface mutation pages (tools,
 * voting) opened offline show a page-level online-only state instead, and a
 * queued write (`QUEUED_WRITES`, ADR-0038) is never gated: it waits for the
 * connection.
 */
export function offlineWriteGate() {
	const toastService = getToastService();

	return {
		get blocked(): boolean {
			return !reachability.current;
		},
		guard<A extends unknown[]>(action: (...args: A) => void): (...args: A) => void {
			return (...args) => {
				if (reachability.current) {
					action(...args);
					return;
				}
				// A guarded form submit or link click must not fall through to the
				// browser's own navigation.
				const [first] = args;
				if (first instanceof Event) first.preventDefault();
				// Mirrors the page-level "…доступно только онлайн" empty states (voting,
				// tools) so a blocked control and a blocked page speak with one voice.
				toastService.add(m.offline_action_hint(), 'info');
			};
		}
	};
}
