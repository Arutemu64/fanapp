<script lang="ts">
	import { page } from '$app/state';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { statusTitle } from '$lib/utils/errorTitle';

	// Passed by SvelteKit's rendering-error boundary (handleRenderingErrors).
	let { error }: { error?: App.Error } = $props();

	let status = $derived(page.status);
	let title = $derived(statusTitle(status));
</script>

<svelte:head>
	<title>{title} ({status}) · ФАН ФАН</title>
</svelte:head>

<!-- Global fallback: no app shell above this boundary, so render full screen. -->
<ErrorState variant="fullscreen" {error} />
