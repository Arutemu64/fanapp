import { ref } from 'vue';

/**
 * Document foreground/background state as a *reactive* read.
 *
 * Several surfaces need to know whether the tab is in front — the home hero
 * pauses its countdown ticker while hidden (background timers aren't reliably
 * throttled), the schedule refetches on return to catch an SSE event missed
 * during a short background trip. This shares one `visibilitychange`
 * subscription across every reader rather than each wiring its own listener.
 *
 * Module-global (not provided through the app), matching `reachability.ts`: this
 * is a device/document fact, not user- or session-scoped state, so it needn't
 * reset across login/logout. The listener lives as long as the page.
 */
const visible = ref(typeof document === 'undefined' || document.visibilityState === 'visible');

if (typeof document !== 'undefined') {
	document.addEventListener('visibilitychange', () => {
		visible.value = document.visibilityState === 'visible';
	});
}

export const documentVisibility = {
	get current(): boolean {
		return visible.value;
	}
};
