<script lang="ts">
	import { Badge } from 'flowbite-svelte';
	import {
		ClockOutline,
		HourglassOutline,
		BellActiveSolid,
		PlayOutline,
		BellActiveOutline,
		ShuffleOutline,
		EyeOutline,
		EyeSlashOutline,
		BanOutline
	} from 'flowbite-svelte-icons';
	import type { CurrentUserDTO } from '$lib/types/user';
	import { formatDuration, formatUntil, pluralize } from '$lib/utils/formatters';
	import { canManageSchedule } from '$lib/utils/permissions';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createApiClient } from '$lib/api';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import MoveEventModal from './MoveEventModal.svelte';
	import SubscribeModal from './SubscribeModal.svelte';
	import UnsubscribeModal from './UnsubscribeModal.svelte';
	import ConfirmActionModal from './ConfirmActionModal.svelte';

	const client = createApiClient();

	interface Props {
		event: ScheduleEventFullDTO;
		schedule: ScheduleEventFullDTO[];
		currentEvent: ScheduleEventFullDTO | null;
		user: CurrentUserDTO | null;
	}

	let { event, schedule, currentEvent, user }: Props = $props();
	const toastService = getToastService();

	let moveModal = $state(false);
	let subscribeModal = $state(false);
	let unsubscribeModal = $state(false);

	// Confirmation dialog for management actions. Each one broadcasts an
	// irreversible push, so the action only runs after the staffer confirms.
	type ConfirmConfig = {
		title: string;
		message: string;
		confirmLabel: string;
		color: 'primary' | 'red';
		run: () => void;
	};
	let confirmOpen = $state(false);
	let confirmConfig = $state<ConfirmConfig | null>(null);

	// Pad the public number to three digits, e.g. 7 → "007".
	let eventNumber = $derived(event.number.toString().padStart(3, '0'));

	// Optimistic skip flag: the row reflects the toggle instantly instead of waiting
	// for the schedule_updated SSE reload (flaky con wifi can delay it for seconds).
	// null = trust the server-loaded prop; otherwise show our pending guess.
	let optimisticSkipped = $state<boolean | null>(null);
	let isSkipped = $derived(optimisticSkipped ?? event.is_skipped);

	// Once the reloaded schedule confirms our guess, drop the override so external
	// changes (another staffer skipping the same event) flow through again.
	$effect(() => {
		if (optimisticSkipped !== null && event.is_skipped === optimisticSkipped) {
			optimisticSkipped = null;
		}
	});

	// How far ahead this event is compared to the one on stage now.
	// Returns null if either value is missing or the event has already passed.
	function aheadOf(value: number | null, currentValue: number | null): number | null {
		if (value === null || currentValue === null) return null;
		const diff = value - currentValue;
		return diff >= 0 ? diff : null;
	}

	let queueUntil = $derived(currentEvent ? aheadOf(event.queue, currentEvent.queue) : null);
	let timeUntil = $derived(
		currentEvent ? aheadOf(event.time_until, currentEvent.time_until) : null
	);

	async function handleMarkCurrent() {
		const { error, response } = await client.PATCH('/schedule/{event_id}/current', {
			params: { path: { event_id: event.id } }
		});

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		// Instant ack: the inline state only updates after the schedule_updated
		// SSE reload round-trips, so a toast confirms the action immediately.
		toastService.add('Выступление отмечено как текущее', 'success');
	}

	async function handleUnmarkCurrent() {
		const { error, response } = await client.DELETE('/schedule/current');

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		toastService.add('Отметка снята', 'success');
	}

	async function handleToggleSkip() {
		const newIsSkipped = !isSkipped;
		// Flip the row immediately; revert below if the request fails.
		optimisticSkipped = newIsSkipped;

		const { error, response } = newIsSkipped
			? await client.PATCH('/schedule/{event_id}/skip', {
					params: { path: { event_id: event.id } }
				})
			: await client.PATCH('/schedule/{event_id}/unskip', {
					params: { path: { event_id: event.id } }
				});

		if (error || !response.ok) {
			optimisticSkipped = null;
			toastService.error(error);
			return;
		}

		const toastMessage = newIsSkipped
			? 'Выступление помечено как пропущенное'
			: 'Выступление возвращено в расписание';
		toastService.add(toastMessage, 'success');
	}

	function handleSubscribe() {
		if (!user) {
			toastService.add('Войди в аккаунт, чтобы подписаться', 'error');
			return;
		}
		subscribeModal = true;
	}

	function handleUnsubscribe() {
		unsubscribeModal = true;
	}

	// Open the confirm dialog for marking / unmarking the current event.
	function askToggleCurrent() {
		confirmConfig = event.is_current
			? {
					title: 'Снять отметку',
					message: 'Снять отметку текущего выступления?',
					confirmLabel: 'Снять',
					color: 'primary',
					run: handleUnmarkCurrent
				}
			: {
					title: 'Отметить текущим',
					message: `Отметить «${event.title}» как текущее выступление?`,
					confirmLabel: 'Отметить',
					color: 'primary',
					run: handleMarkCurrent
				};
		confirmOpen = true;
	}

	// Open the confirm dialog for skipping / restoring the event.
	function askToggleSkip() {
		confirmConfig = isSkipped
			? {
					title: 'Вернуть выступление',
					message: `Вернуть «${event.title}» в расписание?`,
					confirmLabel: 'Вернуть',
					color: 'primary',
					run: handleToggleSkip
				}
			: {
					title: 'Пропустить выступление',
					message: `Пропустить «${event.title}»? Оно будет помечено как пропущенное.`,
					confirmLabel: 'Пропустить',
					color: 'red',
					run: handleToggleSkip
				};
		confirmOpen = true;
	}
</script>

<div
	class={[
		'flex items-start gap-3 px-3 py-3 transition-colors sm:px-4',
		event.is_current && 'bg-green-50 dark:bg-green-900/20',
		isSkipped && !event.is_current && 'bg-gray-50/70 dark:bg-gray-900/40'
	]}
>
	<!-- Keep the public number visible so the list stays easy to scan on mobile. -->
	<div
		class={[
			'flex w-12 shrink-0 flex-col items-center rounded-lg border px-1.5 py-1.5 text-center',
			event.is_current
				? 'border-green-200 bg-white dark:border-green-600 dark:bg-gray-800'
				: 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900'
		]}
	>
		<!-- Signature element: scrolls past hundreds of times, so it carries the brand. -->
		<span
			class="text-xs font-bold tracking-widest text-primary-500 uppercase dark:text-primary-400"
		>
			№
		</span>
		<span
			class="font-display text-base leading-none font-bold text-gray-900 tabular-nums dark:text-white"
			>{eventNumber}</span
		>
	</div>

	<div class="min-w-0 flex-1">
		<div class="flex items-start gap-2">
			<div class="min-w-0 flex-1">
				<h3
					class={[
						'text-sm leading-snug font-semibold text-gray-900 sm:text-base dark:text-white',
						isSkipped && 'line-through'
					]}
				>
					{event.title}
				</h3>

				<!-- Colored state badges get their own row so they read as a distinct tier above the quiet meta, and wrap predictably on narrow screens. Rendered only when a state is present, so the common no-badge row stays single-line. -->
				{#if event.is_current || isSkipped}
					<div class="mt-1.5 flex flex-wrap items-center gap-1.5">
						{#if event.is_current}
							<Badge
								color="green"
								border
								class="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium"
							>
								<!-- Pulsing live dot reads as "on stage now" at a glance. animate-ping is muted under reduced-motion via global CSS. -->
								<span class="relative flex h-2 w-2" aria-hidden="true">
									<span
										class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-75"
									></span>
									<span class="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
								</span>
								Сейчас
							</Badge>
						{/if}

						{#if isSkipped}
							<Badge
								color="red"
								border
								class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
							>
								<BanOutline class="h-3.5 w-3.5" />
								Пропущено
							</Badge>
						{/if}
					</div>
				{/if}

				<!-- Quiet meta row: duration, countdown, subscription — muted text, no colored chip. -->
				<div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
					<span
						class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400"
					>
						<ClockOutline class="h-3.5 w-3.5" />
						{formatDuration(event.duration)}
					</span>

					{#if timeUntil !== null && timeUntil !== 0}
						<span
							class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400"
						>
							<HourglassOutline class="h-3.5 w-3.5" />
							{formatUntil(queueUntil ?? 0, timeUntil)}
						</span>
					{/if}

					{#if event.user_subscription}
						<!-- Subscription threshold is personal meta, not event state: muted text like duration. The right-side bell carries the colored "subscribed" marker. -->
						<span
							class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400"
						>
							<BellActiveSolid class="h-3.5 w-3.5" />
							Напомним за {event.user_subscription.counter}
							{pluralize(
								event.user_subscription.counter,
								'выступление',
								'выступления',
								'выступлений'
							)}
						</span>
					{/if}
				</div>
			</div>

			<!-- Personal action: the bell stays top-right for every user, separate from the staff strip below. -->
			<div class="ml-auto shrink-0">
				<!-- Inline bell: subscribe/unsubscribe in one tap. -->
				<button
					onclick={event.user_subscription ? handleUnsubscribe : handleSubscribe}
					class={[
						'flex h-11 w-11 items-center justify-center rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:outline-none',
						event.user_subscription
							? 'text-primary-600 hover:bg-primary-50 dark:text-primary-400 dark:hover:bg-primary-900/20'
							: 'text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:text-gray-500 dark:hover:bg-gray-700 dark:hover:text-gray-300'
					]}
					aria-label={event.user_subscription ? 'Отписаться' : 'Подписаться'}
					aria-pressed={event.user_subscription !== null}
				>
					{#if event.user_subscription}
						<BellActiveSolid class="h-5 w-5" />
					{:else}
						<BellActiveOutline class="h-5 w-5" />
					{/if}
				</button>
			</div>
		</div>

		<!-- Staff management strip: broadcast actions live on their own row so they never crowd the title, and read as "changes the show for everyone" distinct from the personal bell above. -->
		{#if canManageSchedule(user)}
			<div
				class="mt-3 flex flex-wrap items-center justify-end gap-1.5 border-t border-gray-100 pt-2.5 dark:border-gray-800"
			>
				<button
					type="button"
					onclick={askToggleCurrent}
					class="inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:outline-none dark:text-gray-300 dark:hover:bg-gray-700"
				>
					<PlayOutline class="h-4 w-4" />
					{event.is_current ? 'Снять отметку' : 'Отметить текущим'}
				</button>

				<button
					type="button"
					onclick={() => (moveModal = true)}
					class="inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:outline-none dark:text-gray-300 dark:hover:bg-gray-700"
				>
					<ShuffleOutline class="h-4 w-4" />
					Перенести
				</button>

				<button
					type="button"
					onclick={askToggleSkip}
					class={[
						'inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:outline-none',
						isSkipped
							? 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
							: 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20'
					]}
				>
					{#if isSkipped}
						<EyeOutline class="h-4 w-4" />
						Вернуть
					{:else}
						<EyeSlashOutline class="h-4 w-4" />
						Пропустить
					{/if}
				</button>
			</div>
		{/if}
	</div>
</div>

<SubscribeModal bind:open={subscribeModal} {event} />
<UnsubscribeModal bind:open={unsubscribeModal} {event} />
<MoveEventModal bind:open={moveModal} {event} {schedule} />

<!-- Shared confirm dialog for the staff strip's broadcast actions. -->
<ConfirmActionModal
	bind:open={confirmOpen}
	title={confirmConfig?.title ?? ''}
	message={confirmConfig?.message ?? ''}
	confirmLabel={confirmConfig?.confirmLabel ?? ''}
	confirmColor={confirmConfig?.color ?? 'primary'}
	onconfirm={() => confirmConfig?.run()}
/>
