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
	import { formatDuration, formatUntil, pluralize } from '$lib/utils';
	import { canManageSchedule } from '$lib/utils/permissions';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { client } from '$lib/api';
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
		const { data, error, response } = await client.PATCH('/schedule/{event_id}/current', {
			params: { path: { event_id: event.id } }
		});

		if (error) {
			toastService.error(error);
			dropdownOpen = false;
			return;
		}

		toastService.add('Событие отмечено как текущее', 'success');
		dropdownOpen = false;
	}

	async function handleUnmarkCurrent() {
		const { data, error, response } = await client.DELETE('/schedule/current');

		if (error) {
			toastService.error(error);
			dropdownOpen = false;
			return;
		}

		toastService.add('Отметка снята', 'success');
		dropdownOpen = false;
	}

	async function handleToggleSkip() {
		const newIsSkipped = !event.is_skipped;

		const { data, error, response } = newIsSkipped
			? await client.PATCH('/schedule/{event_id}/skip', {
					params: { path: { event_id: event.id } }
				})
			: await client.PATCH('/schedule/{event_id}/unskip', {
					params: { path: { event_id: event.id } }
				});

		if (error) {
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
	class="rounded-lg border bg-white py-2.5 ps-3 pe-2.5 shadow-sm dark:border-gray-700 dark:bg-gray-800 {event.is_current
		? 'border-green-400 ring-2 ring-green-400 dark:border-green-500 dark:ring-green-500'
		: 'border-gray-200'}"
>
	<div class="flex items-center gap-2 sm:gap-3">
		<div
			class="flex w-16 shrink-0 items-center justify-center text-4xl font-bold text-gray-900 sm:w-20 sm:text-3xl dark:text-white"
		>
			{event.public_number?.toString().padStart(3, '0')}
		</div>

		<div class="h-7 w-px self-center bg-gray-200 sm:h-9 dark:bg-gray-700"></div>

		<div class="min-w-0 flex-1">
			<h3
				class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white"
				class:line-through={event.is_skipped}
			>
				{event.title}
			</h3>
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
				{#if event.is_current}
					<Badge color="green" border class="inline-flex items-center gap-1 text-sm">
						<PlayOutline class="me-1 h-4 w-4" />
						Сейчас
					</Badge>
				{/if}

				{#if event.is_skipped}
					<Badge color="red" border class="inline-flex items-center gap-1 text-sm">
						<BanOutline class="me-1 h-4 w-4" />
						Пропущено
					</Badge>
				{/if}

				<Badge color="gray" border class="inline-flex items-center gap-1 text-sm">
					<ClockOutline class="me-1 h-4 w-4" />
					{formatDuration(event.duration)}
				</Badge>

				{#if timeUntil !== null && timeUntil !== 0}
					<Badge color="yellow" border class="inline-flex items-center gap-1 text-sm">
						<HourglassOutline class="me-1 h-4 w-4" />
						{formatUntil(queueUntil ?? 0, timeUntil)}
					</Badge>
				{/if}

				{#if event.user_subscription}
					<Badge color="blue" border class="inline-flex items-center gap-1 text-sm">
						<BellActiveSolid class="me-1 h-4 w-4" />
						{event.user_subscription.counter}
						{pluralize(event.user_subscription.counter, 'событие', 'события', 'событий')}
					</Badge>
				{/if}
			</div>
		</div>

		<button
			id={dropdownId}
			class="ml-auto flex shrink-0 items-center justify-center self-stretch rounded-lg px-3 text-gray-500 hover:bg-gray-100 focus:ring-2 focus:ring-primary-300 focus:outline-none dark:text-gray-400 dark:hover:bg-gray-700"
			aria-label="Меню действий"
		>
			<DotsVerticalOutline class="h-6 w-6" />
		</button>
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
