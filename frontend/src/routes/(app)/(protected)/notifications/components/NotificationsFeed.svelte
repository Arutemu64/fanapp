<script lang="ts">
	import { resolve } from '$app/paths';
	import Bell from '@lucide/svelte/icons/bell';
	import Settings from '@lucide/svelte/icons/settings';
	import {
		createInfiniteQuery,
		createMutation,
		createQuery,
		useQueryClient
	} from '@tanstack/svelte-query';
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';

	import type { NotificationDto } from '#lib/api/generated/index.js';

	import {
		countUnreadNotificationsOptions,
		countUnreadNotificationsQueryKey,
		listUserNotificationsQueryKey,
		markAllNotificationsReadMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	// A plain SDK call, not a mutation: read-on-view is a background sync no one
	// submits, with its own retry bookkeeping (requestedReadIds below).
	import { markNotificationsRead } from '#lib/api/generated/index.js';
	import { notificationsFeedOptions } from '#lib/api/offlineQueries.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { MARK_READ_BATCH_MAX } from '#lib/constants/notifications.js';
	import { m } from '#lib/paraglide/messages.js';
	import { documentVisibility } from '#lib/services/documentVisibility.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { minuteClock } from '#lib/services/minuteClock.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { queryView } from '#lib/utils/queryView.js';

	import { groupByDay } from '../groupByDay.js';
	import NotificationListItem from './NotificationListItem.svelte';
	import NotificationsSkeleton from './NotificationsSkeleton.svelte';

	const queryClient = useQueryClient();
	const toastService = getToastService();
	const eventsClient = getEventsClient();

	// The bell shows the same query, so clearing it here clears the badge too.
	const unreadQuery = createQuery(() => countUnreadNotificationsOptions());
	let unreadCount = $derived(unreadQuery.data?.count ?? 0);

	// New arrivals (SSE) invalidate the query, which refetches every loaded page.
	const notificationsQuery = createInfiniteQuery(() => notificationsFeedOptions());

	let notifications = $derived(
		notificationsQuery.data?.pages.flatMap((page) => page.notifications) ?? []
	);
	let dayGroups = $derived(groupByDay(notifications, minuteClock.now));

	let notificationsView = $derived(
		queryView(notificationsQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.notifications_load_failed()
		})
	);

	// This page shows no push toast (the item lands in the list instead), so it
	// announces arrivals to screen readers itself.
	let liveAnnouncement = $state('');

	// Ids that were unseen when they reached this screen. Each stays marked "new"
	// for as long as the screen is open, even once a refetch brings it back with the
	// seen_at this visit recorded: clearing the dot the moment the mark-read request
	// lands would erase the one cue telling the user which items they haven't seen
	// yet. The next visit shows them as seen.
	const unseenOnArrival = new SvelteSet<NotificationDto['id']>();

	function isNew(notification: NotificationDto): boolean {
		return !notification.seen_at || unseenOnArrival.has(notification.id);
	}

	let newCount = $derived(notifications.filter(isNew).length);

	// Ids already sent (or in flight) to mark-read, so each one is posted once.
	// Deliberately not reactive: the effect below reads it, and a failed request
	// removing ids would re-run the effect and retry in a tight loop while offline.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- non-reactive on purpose, see above
	const requestedReadIds = new Set<NotificationDto['id']>();

	// Holds back "Прочитать все" until the opening mark-read round has settled:
	// before that the shared count still includes the on-screen items about to be
	// marked, and the button would flash for a round-trip on every visit.
	let openingReadSettled = $state(false);

	// Unread items the screen can't mark on view: older than every loaded page, or
	// arrived while the app was in the background.
	let showMarkAll = $derived(openingReadSettled && unreadCount > 0);

	async function markRead(ids: Array<NotificationDto['id']>) {
		for (const id of ids) {
			requestedReadIds.add(id);
			unseenOnArrival.add(id);
		}

		let markedAny = false;
		for (let start = 0; start < ids.length; start += MARK_READ_BATCH_MAX) {
			const batch = ids.slice(start, start + MARK_READ_BATCH_MAX);
			const { error, response } = await markNotificationsRead({
				body: { notification_ids: batch }
			});
			if (error || !response?.ok) {
				// Retried with the next batch the effect below sends.
				for (const id of batch) {
					requestedReadIds.delete(id);
				}
			} else {
				markedAny = true;
			}
		}
		if (!markedAny) return;

		await queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() });
		// The cached feed still carries these as unseen. Mark it stale without
		// refetching every loaded page now (unseenOnArrival keeps this visit's dots),
		// so the next visit refetches instead of showing them as new again.
		void queryClient.invalidateQueries({
			queryKey: listUserNotificationsQueryKey(),
			refetchType: 'none'
		});
	}

	// Read-on-view: an item counts as read once it is on this screen while the app
	// is in front — the opening page, each "Показать ещё" page, live arrivals. The
	// feed is informational (programme changes, reminders, mailings), not a queue
	// of tasks — the case where read-on-open is the recommended default (Courier,
	// "In-app notification center design"). Items that land while the app is in
	// the background wait until it comes back, so nothing is marked read unseen.
	$effect(() => {
		if (!documentVisibility.current) return;
		if (notificationsQuery.data === undefined) return;

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

	const markAllReadMutation = createMutation(() => ({
		...markAllNotificationsReadMutation(),
		onSuccess: async () => {
			// Zero the badge at once, then reconcile with the server: a notification
			// committed between the mark-all and this callback is still unread, and only
			// the refetch surfaces it. Cancelling first stops a count fetched before the
			// mark-all from landing on top of the zero (TanStack's optimistic-update order).
			const queryKey = countUnreadNotificationsQueryKey();
			await queryClient.cancelQueries({ queryKey });
			queryClient.setQueryData(queryKey, { count: 0 });
			await queryClient.invalidateQueries({ queryKey });
		}
	}));

	function markAllRead() {
		markAllReadMutation.mutate(
			{},
			{
				onError: (error) => toastService.error(error, m.notifications_mark_read_failed())
			}
		);
	}

	let listElement = $state<HTMLElement>();

	function announceNotification(notification: NotificationDto) {
		liveAnnouncement = m.notifications_announce_new({ title: notification.title });
	}

	onMount(() => {
		eventsClient.on('notification_created', announceNotification);
		return () => {
			eventsClient.off('notification_created', announceNotification);
		};
	});
</script>

<!-- Rendered before any announcement: a live region injected together with its
	text is not reliably announced. -->
<p class="sr-only" aria-live="polite" aria-atomic="true">{liveAnnouncement}</p>

<QueryState view={notificationsView}>
	{#snippet loading()}
		<NotificationsSkeleton />
	{/snippet}

	{#snippet offline()}
		<EmptyState
			title={m.notifications_offline_title()}
			message={m.notifications_offline_message()}
		/>
	{/snippet}

	{#snippet ready()}
		{#if notifications.length === 0}
			<EmptyState
				icon={Bell}
				title={m.notifications_empty_title()}
				message={m.notifications_empty_message()}
			>
				<Button variant="outline" href={resolve('profile/notifications')}>
					<Settings data-icon="inline-start" />
					{m.notifications_configure()}
				</Button>
			</EmptyState>
		{:else}
			<SectionIntro>
				<div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
					<p class="text-sm text-muted-foreground">
						{#if newCount > 0}
							{m.notifications_new_count({ count: newCount })}
						{:else if unreadCount === 0}
							{m.notifications_all_read()}
						{/if}
					</p>
					<div class="-me-3 flex items-center">
						{#if showMarkAll}
							<Button
								variant="ghost"
								size="sm"
								onclick={markAllRead}
								disabled={markAllReadMutation.isPending}
							>
								{m.notifications_mark_all_read()}
							</Button>
						{/if}
						<Button variant="ghost" size="sm" href={resolve('profile/notifications')}>
							<Settings data-icon="inline-start" />
							{m.notifications_settings()}
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
									<NotificationListItem {notification} isNew={isNew(notification)} />
								</li>
							{/each}
						</ul>
					</section>
				{/each}
			</div>

			<LoadMoreButton
				query={notificationsQuery}
				list={listElement}
				itemSelector="[data-notification-id]"
				errorMessage={m.notifications_load_failed()}
			/>
		{/if}
	{/snippet}
</QueryState>
