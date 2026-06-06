<script lang="ts">
	import { Badge, Dropdown, DropdownItem } from 'flowbite-svelte';
	import {
		ClockOutline,
		HourglassOutline,
		BellActiveSolid,
		DotsVerticalOutline,
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
	const client = createApiClient();
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import MoveEventModal from './MoveEventModal.svelte';
	import SubscribeModal from './SubscribeModal.svelte';
	import UnsubscribeModal from './UnsubscribeModal.svelte';

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

	// Dropdown state
	let dropdownOpen = $state(false);

	// Unique ID for this card's dropdown trigger
	let dropdownId = $derived(`event-menu-${event.id}`);
	let publicNumber = $derived(event.public_number.toString().padStart(3, '0'));

	let queueUntil = $derived(
		currentEvent && event.queue !== null && currentEvent.queue !== null
			? (() => {
					const diff = event.queue - currentEvent.queue;
					return diff >= 0 ? diff : null;
				})()
			: null
	);
	let timeUntil = $derived(
		currentEvent && event.time_until !== null && currentEvent.time_until !== null
			? (() => {
					const diff = event.time_until - currentEvent.time_until;
					return diff >= 0 ? diff : null;
				})()
			: null
	);

	async function handleMarkCurrent() {
		const { error, response } = await client.PATCH('/schedule/{event_id}/current', {
			params: { path: { event_id: event.id } }
		});

		if (error || !response.ok) {
			toastService.error(error);
			dropdownOpen = false;
			return;
		}

		toastService.add('Событие отмечено как текущее', 'success');
		dropdownOpen = false;
	}

	async function handleUnmarkCurrent() {
		const { error, response } = await client.DELETE('/schedule/current');

		if (error || !response.ok) {
			toastService.error(error);
			dropdownOpen = false;
			return;
		}

		toastService.add('Отметка снята', 'success');
		dropdownOpen = false;
	}

	async function handleToggleSkip() {
		const newIsSkipped = !event.is_skipped;

		const { error, response } = newIsSkipped
			? await client.PATCH('/schedule/{event_id}/skip', {
					params: { path: { event_id: event.id } }
				})
			: await client.PATCH('/schedule/{event_id}/unskip', {
					params: { path: { event_id: event.id } }
				});

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		dropdownOpen = false;
		const toastMessage = newIsSkipped
			? 'Событие помечено как пропущенное'
			: 'Событие возвращено в расписание';
		toastService.add(toastMessage, 'success');
	}

	function handleUnsubscribe() {
		unsubscribeModal = true;
	}
</script>

<div
	class={[
		'flex items-start gap-3 px-3 py-3 transition-colors sm:px-4',
		event.is_current && 'bg-green-50/70 dark:bg-green-950/15',
		event.is_skipped && !event.is_current && 'bg-gray-50/70 dark:bg-gray-900/40'
	]}
>
	<!-- Keep the public number visible so the list stays easy to scan on mobile. -->
	<div
		class={[
			'flex w-12 shrink-0 flex-col items-center rounded-lg border px-1.5 py-1.5 text-center',
			event.is_current
				? 'border-green-200 bg-white dark:border-green-800 dark:bg-gray-800'
				: 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900'
		]}
	>
		<span class="text-xs font-medium tracking-wide text-gray-500 uppercase dark:text-gray-400">
			№
		</span>
		<span class="text-base leading-none font-bold text-gray-900 dark:text-white"
			>{publicNumber}</span
		>
	</div>

	<div class="min-w-0 flex-1">
		<div class="flex items-start gap-2">
			<div class="min-w-0 flex-1">
				<h3
					class="text-sm leading-snug font-semibold text-gray-900 sm:text-base dark:text-white"
					class:line-through={event.is_skipped}
				>
					{event.title}
				</h3>

				<div class="mt-1.5 flex flex-wrap items-center gap-1.5">
					{#if event.is_current}
						<Badge
							color="green"
							border
							class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
						>
							<PlayOutline class="h-3.5 w-3.5" />
							Сейчас
						</Badge>
					{/if}

					{#if event.is_skipped}
						<Badge
							color="red"
							border
							class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
						>
							<BanOutline class="h-3.5 w-3.5" />
							Пропущено
						</Badge>
					{/if}

					<Badge
						color="gray"
						border
						class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
					>
						<ClockOutline class="h-3.5 w-3.5" />
						{formatDuration(event.duration)}
					</Badge>

					{#if timeUntil !== null && timeUntil !== 0}
						<Badge
							color="yellow"
							border
							class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
						>
							<HourglassOutline class="h-3.5 w-3.5" />
							{formatUntil(queueUntil ?? 0, timeUntil)}
						</Badge>
					{/if}

					{#if event.user_subscription}
						<Badge
							color="blue"
							border
							class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
						>
							<BellActiveSolid class="h-3.5 w-3.5" />
							{event.user_subscription.counter}
							{pluralize(event.user_subscription.counter, 'событие', 'события', 'событий')}
						</Badge>
					{/if}
				</div>
			</div>

			<button
				id={dropdownId}
				class="ml-auto flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:outline-none dark:text-gray-400 dark:hover:bg-gray-700"
				aria-label="Меню действий"
			>
				<DotsVerticalOutline class="h-5 w-5" />
			</button>
		</div>
	</div>
</div>

<SubscribeModal bind:open={subscribeModal} {event} />
<UnsubscribeModal bind:open={unsubscribeModal} {event} />
<MoveEventModal bind:open={moveModal} {event} {schedule} />

{#snippet menuItems()}
	{#if event.user_subscription}
		<DropdownItem onclick={handleUnsubscribe}>
			<span class="flex items-center gap-2">
				<BellActiveOutline class="h-4 w-4" />
				Отписаться
			</span>
		</DropdownItem>
	{:else}
		<DropdownItem
			onclick={() => {
				if (!user) {
					toastService.add('Необходимо войти в аккаунт для подписки', 'error');
					dropdownOpen = false;
					return;
				}
				subscribeModal = true;
			}}
		>
			<span class="flex items-center gap-2">
				<BellActiveOutline class="h-4 w-4" />
				Подписаться
			</span>
		</DropdownItem>
	{/if}

	{#if canManageSchedule(user)}
		{#if event.is_current}
			<DropdownItem onclick={handleUnmarkCurrent}>
				<span class="flex items-center gap-2">
					<PlayOutline class="h-4 w-4" />
					Снять отметку
				</span>
			</DropdownItem>
		{:else}
			<DropdownItem onclick={handleMarkCurrent}>
				<span class="flex items-center gap-2">
					<PlayOutline class="h-4 w-4" />
					Отметить текущим
				</span>
			</DropdownItem>
		{/if}

		<DropdownItem onclick={() => (moveModal = true)}>
			<span class="flex items-center gap-2">
				<ShuffleOutline class="h-4 w-4" />
				Перенести
			</span>
		</DropdownItem>

		<DropdownItem onclick={handleToggleSkip}>
			<span class="flex items-center gap-2">
				{#if event.is_skipped}
					<EyeOutline class="h-4 w-4" />
					Вернуть
				{:else}
					<EyeSlashOutline class="h-4 w-4" />
					Пропустить
				{/if}
			</span>
		</DropdownItem>
	{/if}
{/snippet}

<Dropdown simple triggeredBy={`#${dropdownId}`} bind:isOpen={dropdownOpen}>
	{@render menuItems()}
</Dropdown>
