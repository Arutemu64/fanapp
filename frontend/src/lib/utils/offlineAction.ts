import { reachability } from '#lib/services/reachability.js';
import { getToastService } from '#lib/services/toasts.svelte.js';

/**
 * Shown when someone taps a write control while the backend is unreachable.
 * Mirrors the page-level "…доступно только онлайн" empty states (voting,
 * feedback, tools) so a blocked control and a blocked page speak with one voice.
 */
const OFFLINE_ACTION_HINT = 'Доступно только онлайн';

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
 * (or `onsubmit`, `onCheckedChange`). Whole-surface mutation pages (feedback,
 * tools, voting) opened offline show a page-level online-only state instead.
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
				toastService.add(OFFLINE_ACTION_HINT, 'info');
			};
		}
	};
}
