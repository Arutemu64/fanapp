import { computed } from 'vue';

import { reachability } from '#lib/services/reachability.js';

/**
 * Hint shown on a write control that is disabled because the backend is
 * unreachable. Mirrors the page-level "…доступно только онлайн" empty states
 * (voting, feedback, tools) so a disabled button and a blocked page speak with
 * one voice.
 */
const OFFLINE_ACTION_HINT = 'Доступно только онлайн';

/**
 * Reactive gate for write controls on pages that stay *readable* offline
 * (profile, schedule): the cached content is worth showing, but the mutations on
 * top of it are online-only (docs §"PWA & Offline Support" — "Mutations stay
 * online-only"). Rather than let a tap fail into an error toast, the trigger
 * degrades to a disabled state with a hint.
 *
 * Both values are computeds over reactive reachability, so binding
 * `:disabled="disabled"` in markup re-evaluates on connectivity changes.
 *
 * One shared gate keeps every write control consistent and impossible to forget:
 * a new button opts in with a single `disabled`/`title` pair rather than
 * hand-rolled per-control logic. Whole-surface mutation pages (feedback, tools,
 * voting) are handled differently — a single page-level online-only state — since
 * they have nothing to read offline.
 */
export function useOfflineWriteGate() {
	const disabled = computed(() => !reachability.current);
	/** `title` for the control: the hint while offline, `undefined` when online. */
	const title = computed(() => (reachability.current ? undefined : OFFLINE_ACTION_HINT));
	return { disabled, title };
}
