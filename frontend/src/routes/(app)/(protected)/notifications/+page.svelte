<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';

	import NotificationsFeed from './components/NotificationsFeed.svelte';
</script>

<svelte:head>
	<title>{m.document_title({ title: m.notifications_title() })}</title>
</svelte:head>

<NotificationsFeed />
