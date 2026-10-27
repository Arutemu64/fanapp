<script lang="ts">
	import ErrorState from '#lib/components/ErrorState.svelte';

	let { error }: { error?: App.Error } = $props();
</script>

<ErrorState variant="inline" {error} />
