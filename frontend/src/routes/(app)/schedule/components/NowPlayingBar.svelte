<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { BellRing, SkipForward } from '@lucide/svelte';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';
	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import { setEventAsCurrent } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { formatEventNumber, pluralize } from '#lib/utils/formatters.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';
	import { canManageSchedule } from '#lib/utils/permissions.js';

	import ConfirmActionModal from './ConfirmActionModal.svelte';

	interface Props {
		current: ScheduleEventWithSubscription;
		/** The act the staff "next" button puts on stage; null after the last act. */
		next: ScheduleEventWithSubscription | null;
		/** The viewer's nearest subscribed act ahead of the stage, with its queue distance. */
		nextSubscribed: { event: ScheduleEventWithSubscription; actsAway: number } | null;
		user: CurrentUserDto | null;
		onjump: () => void;
	}

	let { current, next, nextSubscribed, user, onjump }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();
	const offlineGate = offlineWriteGate();

	let confirmOpen = $state(false);

	let currentNumber = $derived(formatEventNumber(current.number));
	let showNextButton = $derived(canManageSchedule(user) && next !== null);

	let subscribedHint = $derived.by(() => {
		if (!nextSubscribed) return null;
		const { actsAway } = nextSubscribed;
		return `через ${actsAway} ${pluralize(actsAway, 'выступление', 'выступления', 'выступлений')}`;
	});

	// Captured when the dialog opens: a schedule_updated reload while it is open
	// could move `next`, and the staffer must get the act the dialog named.
	let confirmTarget = $state<ScheduleEventWithSubscription | null>(null);

	function askNext() {
		confirmTarget = next;
		confirmOpen = true;
	}

	async function markNextCurrent() {
		const target = confirmTarget;
		if (!target) return;

		const { error, response } = await setEventAsCurrent({
			client,
			path: { event_id: target.id }
		});

		if (error || !response?.ok) {
			toastService.error(error);
			return;
		}

		// Read-your-writes, as in EventCard: don't wait for the SSE echo.
		void invalidate('app:schedule');
		toastService.add('Выступление отмечено как текущее', 'success');
	}
</script>

<!-- The iOS 26 tab-bar "bottom accessory" shape (Apple Music's now-playing bar): one
	compact glass row above the bottom nav, tap to jump to the act. Kept to two lines
	because a persistent bar costs screen space on every scroll position
	(https://www.nngroup.com/articles/sticky-headers/). -->
<div
	class="pointer-events-auto flex items-center gap-1 rounded-2xl border border-border/60 bg-background/85 p-1 shadow-lg shadow-black/5 backdrop-blur-lg backdrop-saturate-150 reduced-transparency:bg-background reduced-transparency:backdrop-blur-none"
>
	<button
		type="button"
		onclick={onjump}
		class="flex min-h-12 min-w-0 flex-1 items-center gap-3 rounded-xl px-2.5 py-1.5 text-left transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none"
		aria-label={`Сейчас на сцене: ${current.title}. Перейти к выступлению`}
	>
		<span class="relative flex size-2.5 shrink-0" aria-hidden="true">
			<span class="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75"
			></span>
			<span class="relative inline-flex size-2.5 rounded-full bg-success"></span>
		</span>

		<span class="flex min-w-0 flex-1 flex-col">
			<span class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
				<span class="text-success">Сейчас</span>
				{#if currentNumber !== null}
					<span class="tabular-nums">№{currentNumber}</span>
				{/if}
				{#if subscribedHint}
					<span aria-hidden="true">·</span>
					<span class="inline-flex min-w-0 items-center gap-1 text-primary">
						<BellRing class="size-3 shrink-0" />
						<span class="truncate">{subscribedHint}</span>
					</span>
				{/if}
			</span>
			<span class="truncate text-sm leading-snug font-semibold text-foreground">
				{current.title}
			</span>
		</span>
	</button>

	{#if showNextButton}
		<button
			type="button"
			onclick={askNext}
			disabled={offlineGate.disabled}
			aria-label="Следующее выступление"
			title={offlineGate.disabled ? offlineGate.title : 'Следующее выступление'}
			class="inline-flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors hover:bg-primary/20 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40"
		>
			<SkipForward class="size-5 fill-current" />
		</button>
	{/if}
</div>

{#if confirmOpen && confirmTarget}
	<ConfirmActionModal
		bind:open={confirmOpen}
		title="Следующее выступление"
		message={`Отметить «${confirmTarget.title}» как текущее выступление?`}
		confirmLabel="Отметить"
		confirmColor="primary"
		notifyTone="warning"
		onconfirm={() => void markNextCurrent()}
	/>
{/if}
