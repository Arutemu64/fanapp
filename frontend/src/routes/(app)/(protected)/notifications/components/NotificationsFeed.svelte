<script lang="ts">
	import { resolve } from '$app/paths';
	import { Bell, Settings } from '@lucide/svelte';
	import { onMount, tick } from 'svelte';

	import type { NotificationDto } from '#lib/api/generated/index.js';

	import {
		listUserNotifications,
		markAllNotificationsRead,
		markNotificationsRead
	} from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import {
		NOTIFICATION_PAGE_REQUEST_LIMIT,
		NOTIFICATION_PAGE_SIZE
	} from '#lib/constants/notifications.js';
	import { documentVisibility } from '#lib/services/documentVisibility.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { PaginatedFeed } from '#lib/services/feed.svelte.js';
	import { minuteClock } from '#lib/services/minuteClock.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { getUnreadCountService } from '#lib/services/unreadCount.svelte.js';
	import { dedupeById } from '#lib/utils/feed.js';

	import { groupByDay } from '../groupByDay.js';
	import NotificationListItem from './NotificationListItem.svelte';

	const client = createApiClient();

	interface Props {
		initialNotifications: Array<NotificationDto>;
		initialHasMore: boolean;
	}

	let { initialNotifications, initialHasMore }: Props = $props();

	const toastService = getToastService();
	const eventsClient = getEventsClient();
	const unread = getUnreadCountService();

	const feed = new PaginatedFeed<NotificationDto>({
		pageSize: NOTIFICATION_PAGE_SIZE,
		requestLimit: NOTIFICATION_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialNotifications,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await listUserNotifications({
				client,
				query: { limit, offset }
			});
			return error || !data ? null : data.notifications;
		},
		onError: () => toastService.add('Не удалось загрузить уведомления', 'error')
	});

	// Notifications pushed over SSE — kept on top, newest first.
	let liveNotifications = $state.raw<Array<NotificationDto>>([]);

	// Fresh SSE items on top, then the server page and anything loaded after it.
	let notifications = $derived(dedupeById(liveNotifications, feed.items));
	let dayGroups = $derived(groupByDay(notifications, minuteClock.now));

	// The DTOs keep the seen_at they were fetched with, so an item that was unseen
	// when it reached this screen stays marked "new" for as long as the screen is
	// open, even after the server has recorded it as read. Clearing the dot the
	// moment the mark-read request lands would erase the one cue telling the user
	// which items they haven't seen yet; the next visit fetches them as seen.
	let newCount = $derived(notifications.filter((notification) => !notification.seen_at).length);

	// Ids already sent (or in flight) to mark-read, so each one is posted once.
	// Deliberately not reactive: the effect below reads it, and a failed request
	// removing ids would re-run the effect and retry in a tight loop while offline.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const requestedReadIds = new Set<NotificationDto['id']>();

	// Holds back "Прочитать все" until the opening mark-read round has settled:
	// before that the shared count still includes the on-screen items about to be
	// marked, and the button would flash for a round-trip on every visit.
	let openingReadSettled = $state(false);
	let isMarkingAll = $state(false);

	// Unread items the screen can't mark on view: older than every loaded page, or
	// arrived while the app was in the background.
	let showMarkAll = $derived(openingReadSettled && unread.count > 0);

	async function markRead(ids: Array<NotificationDto['id']>) {
		for (const id of ids) {
			requestedReadIds.add(id);
		}

		const { error, response } = await markNotificationsRead({
			client,
			body: { notification_ids: ids }
		});
		if (error || !response?.ok) {
			// Retried with the next batch the effect below sends.
			for (const id of ids) {
				requestedReadIds.delete(id);
			}
			return;
		}

		await unread.refresh();
	}

	// Read-on-view: an item counts as read once it is on this screen while the app
	// is in front — the opening page, each "Показать ещё" page, live arrivals. The
	// feed is informational (programme changes, reminders, mailings), not a queue
	// of tasks — the case where read-on-open is the recommended default (Courier,
	// "In-app notification center design"). Items that land while the app is in
	// the background wait until it comes back, so nothing is marked read unseen.
	$effect(() => {
		if (!documentVisibility.current) return;

		const unseenIds = notifications
			.filter((notification) => !notification.seen_at && !requestedReadIds.has(notification.id))
			.map((notification) => notification.id);

		if (unseenIds.length === 0) {
			openingReadSettled = true;
			return;
		}

		void markRead(unseenIds).finally(() => {
			openingReadSettled = true;
		});
	});

	async function markAllRead() {
		isMarkingAll = true;
		const { error, response } = await markAllNotificationsRead({ client });
		isMarkingAll = false;

		if (error || !response?.ok) {
			toastService.error(error, 'Не удалось отметить уведомления прочитанными');
			return;
		}

		// Clear for instant feedback, then reconcile with the server: a notification
		// committed between the mark-all and this handler is still unread, and only a
		// follow-up refresh surfaces it (the clear's own guard drops a stale pre-mark
		// refresh, so this can't restore the old total).
		unread.clear();
		await unread.refresh();
	}

	let listElement = $state<HTMLElement>();

	// Move focus to the first item of the page just loaded, the usual advice for a
	// load-more control: keyboard and screen-reader users continue where the new
	// content starts, and focus isn't dropped to <body> when the button unmounts
	// after the last page. Matched by id against the fetched pages only, since live
	// arrivals can be prepended while the request is in flight.
	async function loadMore() {
		const idsBefore = new Set(feed.items.map((notification) => notification.id));
		await feed.loadMore();

		let target = feed.items.find((notification) => !idsBefore.has(notification.id));
		// An empty or all-duplicate last page adds nothing but still removes the
		// button, so hand focus to the end of the list instead.
		if (!target && !feed.hasMore) {
			target = notifications.at(-1);
		}
		if (!target) return;

		await tick();
		const item = listElement?.querySelector<HTMLElement>(
			`[data-notification-id="${CSS.escape(target.id)}"]`
		);
		const link = item?.querySelector<HTMLElement>('a');
		(link ?? item)?.focus();
	}

	function addLiveNotification(notification: NotificationDto) {
		liveNotifications = dedupeById([notification], liveNotifications);
	}

	// Refetch the first page and lift anything not yet in the list to the top, so we
	// don't lose notifications that arrived while the SSE channel was disconnected.
	async function syncLatestNotifications() {
		const { data: result, error } = await listUserNotifications({
			client,
			query: { limit: NOTIFICATION_PAGE_SIZE }
		});

		if (error || !result) {
			return;
		}

		// Live items count as known too: by now they may be marked read, and the
		// server copy would replace them and drop their "new" flag mid-visit.
		const knownIds = new Set(notifications.map((notification) => notification.id));
		const fresh = result.notifications.filter((notification) => !knownIds.has(notification.id));
		liveNotifications = dedupeById(fresh, liveNotifications);
	}

	function syncAfterReconnect() {
		void syncLatestNotifications();
	}

	onMount(() => {
		eventsClient.on('notification_created', addLiveNotification);
		// 'connection_established' fires on the first connect and on every reconnect.
		eventsClient.on('connection_established', syncAfterReconnect);

		return () => {
			eventsClient.off('notification_created', addLiveNotification);
			eventsClient.off('connection_established', syncAfterReconnect);
		};
	});
</script>

{#if notifications.length === 0}
	<EmptyState
		icon={Bell}
		title="Уведомлений пока нет"
		message="Здесь появятся напоминания о&nbsp;выступлениях из подписок, изменения в&nbsp;программе и&nbsp;рассылки организаторов."
	>
		<Button variant="outline" href={resolve('profile/notifications')}>
			<Settings data-icon="inline-start" />
			Настроить уведомления
		</Button>
	</EmptyState>
{:else}
	<SectionIntro>
		<div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
			<p class="text-sm text-muted-foreground">
				{#if newCount > 0}
					Новых: {newCount}
				{:else if unread.count === 0}
					Все уведомления прочитаны
				{/if}
			</p>
			<div class="-me-3 flex items-center">
				{#if showMarkAll}
					<Button variant="ghost" size="sm" onclick={markAllRead} disabled={isMarkingAll}>
						Прочитать все
					</Button>
				{/if}
				<Button variant="ghost" size="sm" href={resolve('profile/notifications')}>
					<Settings data-icon="inline-start" />
					Настройки
				</Button>
			</div>
		</div>
	</SectionIntro>

	<div bind:this={listElement} class="flex flex-col gap-6">
		{#each dayGroups as group (group.key)}
			<section aria-labelledby="notifications-day-{group.key}">
				<h2
					id="notifications-day-{group.key}"
					class="mb-2 text-sm font-semibold text-muted-foreground"
				>
					{group.heading}
				</h2>
				<ul class="flex flex-col gap-3">
					{#each group.items as notification (notification.id)}
						<!-- Focus target after "Показать ещё" for an item without a link. -->
						<li
							data-notification-id={notification.id}
							tabindex="-1"
							class="rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
						>
							<NotificationListItem {notification} />
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	</div>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={loadMore} />
	{/if}
{/if}
