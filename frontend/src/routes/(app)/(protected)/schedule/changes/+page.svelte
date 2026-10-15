<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';

	import ScheduleChangesFeed from './components/ScheduleChangesFeed.svelte';
</script>

<svelte:head>
	<title>{m.document_title({ title: m.schedule_changes_title() })}</title>
</svelte:head>

<ScheduleChangesFeed />
