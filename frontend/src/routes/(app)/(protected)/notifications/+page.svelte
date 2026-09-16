<script lang="ts">
	import { getApiClient } from '$lib/api/context';
	import { listUserNotificationsOptions } from '$lib/api/queries';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { Button } from '$lib/components/ui/button';
	import {
		NOTIFICATION_PAGE_REQUEST_LIMIT,
		NOTIFICATION_PAGE_SIZE
	} from '$lib/constants/notifications';
	import { offlineQueryState } from '$lib/query/offlineState';
	import { persisted } from '$lib/query/persist';
	import { getOfflineService, shouldShowStaleNotice } from '$lib/services/offline.svelte';
	import { feedSnapshotKey } from '$lib/utils/feed';
	import { createQuery } from '@tanstack/svelte-query';

	import NotificationsFeed from './components/NotificationsFeed.svelte';
	import NotificationsSkeleton from './components/NotificationsSkeleton.svelte';

	const client = getApiClient();
	const offline = getOfflineService();

	// The viewer's own feed: user scope, so it is dropped on logout and can't
	// surface for the next account on a shared device. Cache the raw first page
	// (one item longer than a page) so `hasMore` stays computable offline.
	const notificationsQuery = createQuery(() =>
		persisted(
			listUserNotificationsOptions({
				client,
				query: { limit: NOTIFICATION_PAGE_REQUEST_LIMIT, offset: 0 }
			}),
			'user'
		)
	);

	let firstPage = $derived(notificationsQuery.data?.notifications ?? []);
	let notifications = $derived(firstPage.slice(0, NOTIFICATION_PAGE_SIZE));
	let hasMore = $derived(firstPage.length > NOTIFICATION_PAGE_SIZE);

	// Remount the feed with the fresh server snapshot whenever the query refetches.
	let notificationsKey = $derived(
		feedSnapshotKey(
			hasMore,
			notifications.map((notification) => notification.id)
		)
	);

	let offlineState = $derived(offlineQueryState(notificationsQuery, offline.isOnline));
	let showStaleNotice = $derived(
		shouldShowStaleNotice({
			offlineMiss: offlineState.offlineMiss,
			stale: offlineState.stale,
			isOnline: offline.isOnline
		})
	);

	// Nothing to show and nothing saved: tell a first paint (skeleton) apart from a
	// reachable failure (retry) and from being offline (the page's own empty state).
	let isLoadingFirstPaint = $derived(
		notificationsQuery.isPending && notificationsQuery.data === undefined
	);
	let hasFailed = $derived(notificationsQuery.isError && notificationsQuery.data === undefined);
</script>

<svelte:head>
	<title>Уведомления · ФАН ФАН</title>
</svelte:head>

{#if showStaleNotice}
	<StaleDataNotice
		message="Нет связи. Показаны сохранённые уведомления — обновятся при подключении."
		cachedAt={offlineState.cachedAt}
	/>
{/if}

<!-- The load no longer blocks on the network, so first paint owns the loading
	state the shell's navigation skeleton used to cover. -->
{#if isLoadingFirstPaint}
	<NotificationsSkeleton />
{:else if offlineState.offlineMiss}
	<EmptyState
		title="Уведомления недоступны офлайн"
		message="Появятся после подключения к интернету"
	/>
{:else if hasFailed}
	<!-- A reachable failure is recoverable in place: retry the query instead of
		sending the visitor to a full error page for one bad response. -->
	<EmptyState title="Не удалось загрузить уведомления" message="Проверь связь и попробуй ещё раз">
		<Button variant="outline" size="sm" onclick={() => void notificationsQuery.refetch()}>
			Повторить
		</Button>
	</EmptyState>
{:else}
	{#key notificationsKey}
		<NotificationsFeed initialNotifications={notifications} initialHasMore={hasMore} />
	{/key}
{/if}
