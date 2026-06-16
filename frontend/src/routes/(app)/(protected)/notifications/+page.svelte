<script lang="ts">
	import NotificationsFeed from './components/NotificationsFeed.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Ключ нужен, чтобы после обновления route data компонент списка пересоздался с новым серверным снимком.
	let notificationsKey = $derived(
		`${data.hasMore}:${data.notifications.map((notification) => notification.id).join(':')}`
	);

	// Show the notice when the loaded copy is cached (data.stale) or the device went
	// offline since open — what's on screen may be out of date until reconnect.
	const offline = getOfflineService();
	let showStaleNotice = $derived(data.stale || !offline.isOnline);
</script>

<svelte:head>
	<title>Уведомления · ФАН ФАН</title>
</svelte:head>

{#if showStaleNotice}
	<StaleDataNotice
		message="Нет связи. Показаны сохранённые уведомления — обновятся при подключении."
	/>
{/if}

{#key notificationsKey}
	<NotificationsFeed initialNotifications={data.notifications} initialHasMore={data.hasMore} />
{/key}
