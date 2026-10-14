<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';

	import ScheduleChangesFeed from './components/ScheduleChangesFeed.svelte';
</script>

<svelte:head>
	<title>{m.schedule_changes_title()} · {m.brand_name()}</title>
</svelte:head>

<ScheduleChangesFeed />
