<script lang="ts">
	import CircleAlert from '@lucide/svelte/icons/circle-alert';

	import EmptyState from '#lib/components/EmptyState.svelte';
	import { m } from '#lib/paraglide/messages.js';
</script>

<!-- One screen for every surface that is useless offline (voting, feedback, tools,
	the schedule change log), rendered in place rather than at a route of its own:
	the URL stays put, so the state clears by itself on reconnect and the bottom nav
	still shows where the user is. A cached screen whose copy simply hasn't loaded
	yet says so in its own words instead — see docs/frontend.md §2. -->
<EmptyState
	icon={CircleAlert}
	title={m.offline_unavailable_title()}
	message={m.offline_unavailable_message()}
/>
