import type { EventsClient } from '$lib/services/events.svelte';
import type { ToastService } from '$lib/services/toasts.svelte';

import { goto } from '$app/navigation';
import { resolve } from '$app/paths';

/**
 * Finish a successful login: confirm with a toast, navigate home (revalidating
 * all loaders so the session-aware UI updates), then restart the SSE stream so
 * live events resume under the new identity. Shared by every login form.
 */
export async function completeLogin(
	toastService: ToastService,
	eventsClient: EventsClient | null,
	message: string
): Promise<void> {
	toastService.add(message, 'success');
	await goto(resolve('/'), { invalidateAll: true });
	eventsClient?.restart();
}
