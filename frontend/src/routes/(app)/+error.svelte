<script lang="ts">
	import ErrorState from '$lib/components/ErrorState.svelte';

	// Passed by SvelteKit's rendering-error boundary (handleRenderingErrors).
	let { error }: { error?: App.Error } = $props();
</script>

<!--
	Errors in app routes render here, inside (app)/+layout — so the navbar,
	sidebar and bottom nav stay in place and the user can navigate away.
	Renders in-content rather than taking over the viewport.
-->
<ErrorState variant="inline" {error} />
