<script lang="ts">
	import { page } from '$app/state';

	import ErrorState from '#lib/components/ErrorState.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { statusTitle } from '#lib/utils/errorTitle.js';

	let { error }: { error?: App.Error } = $props();

	let status = $derived(page.status);
	let title = $derived(statusTitle(status));
</script>

<svelte:head>
	<title>{m.document_title({ title: `${title} (${status})` })}</title>
</svelte:head>

<ErrorState variant="fullscreen" {error} />
