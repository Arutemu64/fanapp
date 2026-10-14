<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';

	import NotificationsFeed from './components/NotificationsFeed.svelte';
</script>

<svelte:head>
	<title>{m.notifications_title()} · {m.brand_name()}</title>
</svelte:head>

<NotificationsFeed />
