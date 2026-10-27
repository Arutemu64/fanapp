<script lang="ts">
	import CircleAlert from '@lucide/svelte/icons/circle-alert';

	import EmptyState from '#lib/components/EmptyState.svelte';
	import { m } from '#lib/paraglide/messages.js';
</script>

<EmptyState
	icon={CircleAlert}
	title={m.offline_unavailable_title()}
	message={m.offline_unavailable_message()}
/>
