<script lang="ts">
	import CircleAlert from '@lucide/svelte/icons/circle-alert';

	import * as Alert from '#lib/components/ui/alert/index.js';

	interface Props {
		message: string;
	}

	let { message }: Props = $props();
</script>

{#if message}
	<Alert.Root variant="destructive">
		<CircleAlert aria-hidden="true" />
		<Alert.Description>{message}</Alert.Description>
	</Alert.Root>
{/if}
