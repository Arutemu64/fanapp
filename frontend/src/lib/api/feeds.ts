import type {
	FeedbackDto,
	MailingDto,
	NotificationDto,
	ScheduleChangeFullDto
} from '$lib/api/generated';

import {
	listBroadcastsInfiniteOptions,
	listFeedbackInfiniteOptions,
	listScheduleChangesInfiniteOptions,
	listUserNotificationsInfiniteOptions
} from '$lib/api/generated/@tanstack/svelte-query.gen';
import { offsetPageParams } from '$lib/api/pagination';
import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '$lib/constants/feedback';
import {
	BROADCAST_PAGE_REQUEST_LIMIT,
	BROADCAST_PAGE_SIZE,
	NOTIFICATION_PAGE_REQUEST_LIMIT,
	NOTIFICATION_PAGE_SIZE
} from '$lib/constants/notifications';
import {
	SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
	SCHEDULE_CHANGES_PAGE_SIZE
} from '$lib/constants/schedule_changes';

/**
 * Options for the paginated feeds, defined once each.
 *
 * The generated `*InfiniteOptions()` helpers know how to turn a page param into
 * an `offset`, but `initialPageParam` and `getNextPageParam` are the app's call,
 * so they must be merged in — and by *every* caller. A route that prefetches with
 * the bare generated options writes a cache entry with no `getNextPageParam`,
 * which then throws when a component reads it as an infinite query. Sharing one
 * builder per feed is what stops the load and the component from drifting.
 */

export function notificationsFeedOptions() {
	return {
		...listUserNotificationsInfiniteOptions({
			query: { limit: NOTIFICATION_PAGE_REQUEST_LIMIT }
		}),
		...offsetPageParams(
			(page: { notifications: Array<NotificationDto> }) => page.notifications,
			NOTIFICATION_PAGE_SIZE
		)
	};
}

export function scheduleChangesFeedOptions() {
	return {
		...listScheduleChangesInfiniteOptions({
			query: { limit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT }
		}),
		...offsetPageParams(
			(page: { schedule_changes: Array<ScheduleChangeFullDto> }) => page.schedule_changes,
			SCHEDULE_CHANGES_PAGE_SIZE
		)
	};
}

export function feedbackFeedOptions() {
	return {
		...listFeedbackInfiniteOptions({ query: { limit: FEEDBACK_PAGE_REQUEST_LIMIT } }),
		...offsetPageParams(
			(page: { feedback: Array<FeedbackDto> }) => page.feedback,
			FEEDBACK_PAGE_SIZE
		)
	};
}

export function broadcastsFeedOptions() {
	return {
		...listBroadcastsInfiniteOptions({ query: { limit: BROADCAST_PAGE_REQUEST_LIMIT } }),
		...offsetPageParams(
			(page: { mailings: Array<MailingDto> }) => page.mailings,
			BROADCAST_PAGE_SIZE
		)
	};
}
