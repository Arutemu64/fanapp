<script lang="ts">
	import CircleAlert from '@lucide/svelte/icons/circle-alert';

	import * as Alert from '#lib/components/ui/alert/index.js';

	interface Props {
		/** The whole-form error; nothing renders while it is empty. */
		message: string;
	}

	let { message }: Props = $props();
</script>

<!-- A failure no single field owns (the server refused, the network dropped), shown
	above the form. Field errors stay under their fields. -->
{#if message}
	<Alert.Root variant="destructive">
		<CircleAlert aria-hidden="true" />
		<Alert.Description>{message}</Alert.Description>
	</Alert.Root>
{/if}
