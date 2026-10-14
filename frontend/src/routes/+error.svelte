<script lang="ts">
	import { page } from '$app/state';

	import ErrorState from '#lib/components/ErrorState.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { statusTitle } from '#lib/utils/errorTitle.js';

	// Passed by SvelteKit's rendering-error boundary.
	let { error }: { error?: App.Error } = $props();

	let status = $derived(page.status);
	let title = $derived(statusTitle(status));
</script>

<svelte:head>
	<title>{title} ({status}) · {m.brand_name()}</title>
</svelte:head>

<!-- Global fallback: no app shell above this boundary, so render full screen. -->
<ErrorState variant="fullscreen" {error} />
