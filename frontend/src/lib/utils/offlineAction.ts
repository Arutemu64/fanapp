import { m } from '#lib/paraglide/messages.js';
import { reachability } from '#lib/services/reachability.js';
import { getToastService } from '#lib/services/toasts.svelte.js';

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
				const [first] = args;
				if (first instanceof Event) first.preventDefault();
				toastService.add(m.offline_action_hint(), 'info');
			};
		}
	};
}
