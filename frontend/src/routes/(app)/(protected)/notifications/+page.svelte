<script lang="ts">
	import NotificationsFeed from '$lib/components/notifications/NotificationsFeed.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Ключ нужен, чтобы после обновления route data компонент списка пересоздался с новым серверным снимком.
	let notificationsKey = $derived(
		`${data.hasMore}:${data.notifications.map((notification) => notification.id).join(':')}`
	);
</script>

<svelte:head>
	<title>Уведомления</title>
</svelte:head>

{#key notificationsKey}
	<NotificationsFeed initialNotifications={data.notifications} initialHasMore={data.hasMore} />
{/key}
