import { createSubscriber } from 'svelte/reactivity';

/**
 * Document foreground/background state as a *reactive* read.
 *
 * Several surfaces need to know whether the tab is in front — the home hero
 * pauses its countdown ticker while hidden (background timers aren't reliably
 * throttled), the schedule refetches on return to catch an SSE event missed
 * during a short background trip. Each used to add its own `visibilitychange`
 * listener and re-check `document.visibilityState` by hand; this shares one
 * subscription across every reader instead.
 *
 * Module-global (not Svelte context), matching `reachability.ts`: this is a
 * device/document fact, not user- or session-scoped state, so it needn't reset
 * across login/logout and carries no SSR-leak risk — the getter reads live from
 * the DOM rather than mirroring into stored `$state`.
 */

function documentVisibleNow(): boolean {
	// SSR / non-browser: assume visible, matching the optimistic defaults elsewhere.
	return typeof document === 'undefined' ? true : document.visibilityState === 'visible';
}

// Bridges the DOM event into Svelte's reactivity, so a component can read
// visibility in a $derived or $effect instead of mirroring it into $state.
// One subscription is shared however many readers there are, and it is torn
// down when the last of them goes away.
const subscribeVisible = createSubscriber((update) => {
	document.addEventListener('visibilitychange', update);
	return () => document.removeEventListener('visibilitychange', update);
});

export const documentVisibility = {
	get current(): boolean {
		subscribeVisible();
		return documentVisibleNow();
	}
};
