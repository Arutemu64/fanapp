<script lang="ts">
	import type { ScheduleEventWithSubscription } from '$lib/types/schedule';
	import type { CurrentUserDTO } from '$lib/types/user';

	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { formatDuration, formatUntil, pluralize } from '$lib/utils/formatters';
	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import { canManageSchedule } from '$lib/utils/permissions';
	import {
		Ban,
		Bell,
		BellRing,
		Clock,
		Eye,
		EyeOff,
		Hourglass,
		Play,
		Shuffle,
		XCircle
	} from '@lucide/svelte';

	import ConfirmActionModal from './ConfirmActionModal.svelte';
	import MoveEventModal from './MoveEventModal.svelte';
	import SubscribeModal from './SubscribeModal.svelte';
	import UnsubscribeModal from './UnsubscribeModal.svelte';

	const client = createApiClient();

	interface Props {
		event: ScheduleEventWithSubscription;
		currentEvent: ScheduleEventWithSubscription | null;
		user: CurrentUserDTO | null;
		// 'interlude' for a block-less row (a break, the opening, the closing):
		// drops the number column, since these stand alone rather than in the
		// numbered list. Everything else — the bell, staff actions, the live
		// highlight — stays, so an interlude can still be subscribed to or marked
		// current.
		variant?: 'default' | 'interlude';
	}

	let { event, currentEvent, user, variant = 'default' }: Props = $props();
	const toastService = getToastService();

	// Subscribe/unsubscribe and the staff actions all POST to the server — online
	// only. The cached schedule (and each row's subscription state) still renders.
	const offlineGate = offlineWriteGate();
	// Staff-action labels, hoisted so each button's title stays a single ternary
	// (offline hint vs. action) rather than a nested one in the markup.
	let currentActionLabel = $derived(event.is_current ? 'Снять отметку' : 'Отметить текущим');

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
		// 'warning' for actions that push new info; 'muted' for reverting actions.
		notifyTone: 'warning' | 'muted';
		// The confirm handlers are async; the modal fires them and doesn't await.
		run: () => void | Promise<void>;
	};
	// Two pieces of state, set together when a staff button is tapped:
	// confirmOpen drives the modal's visibility (bound two-way so Esc/backdrop
	// can close it), and confirmConfig holds what that modal should show.
	let confirmOpen = $state(false);
	let confirmConfig = $state<ConfirmConfig | null>(null);

	// Pad the public number to three digits, e.g. 7 → "007". Null for events that
	// have none (breaks and other filler rows), which render no number badge.
	let eventNumber = $derived(event.number === null ? null : String(event.number).padStart(3, '0'));

	// Optimistic skip flag: the row reflects the toggle instantly instead of waiting
	// for the schedule refetch to round-trip (a flaky connection can delay it for
	// seconds). null = trust the server-loaded prop; otherwise show our pending guess.
	let optimisticSkipped = $state<boolean | null>(null);
	let isSkipped = $derived(optimisticSkipped ?? event.is_skipped);
	let skipActionLabel = $derived(isSkipped ? 'Вернуть' : 'Пропустить');

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

	// Queue distance only ("how many acts away"): the schedule carries no predicted
	// clock time (ADR-0014), and the distance decrements as the current-event
	// pointer advances (one set-current SSE per act reloads the schedule).
	let untilLabel = $derived(
		queueUntil === null || queueUntil <= 0 ? null : formatUntil(queueUntil)
	);

	// Read-your-writes: after our own successful mutation, refetch straight off the
	// response instead of waiting for the schedule_updated SSE echo. That echo
	// travels DB → outbox relay → NATS → SSE fan-out before it reaches us, and on a
	// flaky operator connection it can arrive late or be dropped — which would leave
	// the operator who made the change on a stale schedule while everyone else
	// already sees it. The refetch reads committed state (the write closed before
	// the 200), so it is correct even before the relay has ticked; the SSE echo
	// still drives every other client.
	function reloadSchedule() {
		void invalidate('app:schedule');
	}

	async function handleMarkCurrent() {
		const { error, response } = await client.PATCH('/schedule/{event_id}/current', {
			params: { path: { event_id: event.id } }
		});

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		reloadSchedule();
		toastService.add('Выступление отмечено как текущее', 'success');
	}

	async function handleUnmarkCurrent() {
		const { error, response } = await client.DELETE('/schedule/current');

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		reloadSchedule();
		toastService.add('Отметка снята', 'success');
	}

	// `skip` is captured when the confirm dialog opens, not recomputed here: if
	// another staffer flips this event while the modal is open, the schedule_updated
	// reload could change `isSkipped` under us and make a generic toggle broadcast
	// the opposite action from what the dialog promised.
	async function handleSkip(skip: boolean) {
		// Flip the row immediately; revert below if the request fails.
		optimisticSkipped = skip;

		const { error, response } = await client.PATCH('/schedule/{event_id}', {
			params: { path: { event_id: event.id } },
			body: { is_skipped: skip }
		});

		if (error || !response.ok) {
			optimisticSkipped = null;
			toastService.error(error);
			return;
		}

		reloadSchedule();
		const toastMessage = skip
			? 'Выступление помечено как пропущенное'
			: 'Выступление возвращено в программу';
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

	function askToggleCurrent() {
		confirmConfig = event.is_current
			? {
					title: 'Снять отметку',
					message: 'Снять отметку текущего выступления?',
					confirmLabel: 'Снять',
					color: 'primary',
					notifyTone: 'muted',
					run: handleUnmarkCurrent
				}
			: {
					title: 'Отметить текущим',
					message: `Отметить «${event.title}» как текущее выступление?`,
					confirmLabel: 'Отметить',
					color: 'primary',
					notifyTone: 'warning',
					run: handleMarkCurrent
				};
		confirmOpen = true;
	}

	function askToggleSkip() {
		confirmConfig = isSkipped
			? {
					title: 'Вернуть выступление',
					message: `Вернуть «${event.title}» в программу?`,
					confirmLabel: 'Вернуть',
					color: 'primary',
					notifyTone: 'muted',
					// Lock the direction to what the dialog shows now, so a concurrent
					// schedule_updated reload can't flip it before the staffer confirms.
					run: () => handleSkip(false)
				}
			: {
					title: 'Пропустить выступление',
					message: `Пропустить «${event.title}»? Оно будет помечено как пропущенное.`,
					confirmLabel: 'Пропустить',
					color: 'red',
					notifyTone: 'warning',
					run: () => handleSkip(true)
				};
		confirmOpen = true;
	}
</script>

<div
	class={[
		'flex items-start gap-3 px-3 py-4 transition-colors sm:px-4',
		event.is_current && 'bg-success/10',
		isSkipped && !event.is_current && 'bg-muted/50'
	]}
>
	<!-- Interludes stand alone, not in the numbered list, so they drop the number
		column entirely rather than reserving its width. -->
	{#if variant === 'default'}
		<!-- Keep the public number visible so the list stays easy to scan on mobile. -->
		{#if eventNumber !== null}
			<div
				class={[
					'flex w-12 shrink-0 flex-col items-center rounded-lg border px-1.5 py-1.5 text-center',
					event.is_current ? 'border-success/40 bg-card' : 'border-border bg-muted'
				]}
			>
				<!-- Signature element: scrolls past hundreds of times, so it carries the brand. -->
				<span class="text-xs font-bold tracking-widest text-primary uppercase"> № </span>
				<span class="font-display text-base leading-none font-bold text-foreground tabular-nums"
					>{eventNumber}</span
				>
			</div>
		{:else}
			<!-- Numberless rows (breaks) keep the badge's width as empty space: dropping
				it would pull their title out of the column every other row shares, and
				the ragged left edge reads as a broken list while scrolling. -->
			<div class="w-12 shrink-0" aria-hidden="true"></div>
		{/if}
	{/if}

	<div class="min-w-0 flex-1">
		<div class="flex items-start gap-2">
			<div class="min-w-0 flex-1">
				<h3
					class={[
						'text-base leading-snug font-semibold text-foreground',
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
								variant="outline"
								class="inline-flex items-center gap-1.5 border-success/30 bg-success/10 px-2 py-0.5 text-xs font-medium text-success"
							>
								<!-- Pulsing live dot reads as "on stage now" at a glance. animate-ping is muted under reduced-motion via global CSS. -->
								<span class="relative flex h-2 w-2" aria-hidden="true">
									<span
										class="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75"
									></span>
									<span class="relative inline-flex h-2 w-2 rounded-full bg-success"></span>
								</span>
								Сейчас
							</Badge>
						{/if}

						{#if isSkipped}
							<Badge
								variant="destructive"
								class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
							>
								<Ban class="size-3.5" />
								Пропущено
							</Badge>
						{/if}
					</div>
				{/if}

				<!-- Quiet meta row: duration, countdown, subscription — muted text, no colored chip.
				     Every chip aligns its icon to the first line (items-start + mt-px on the icon),
				     not the centre: any chip can wrap to two lines on a narrow phone, and a centred
				     icon would then float in the gap beside the first line. -->
				<div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
					<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
						<Clock class="mt-px size-3.5 shrink-0" />
						{formatDuration(event.duration)}
					</span>

					{#if untilLabel}
						<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
							<Hourglass class="mt-px size-3.5 shrink-0" />
							{untilLabel}
						</span>
					{/if}

					{#if event.user_subscription}
						<!-- Subscription threshold is personal meta, not event state: muted text like duration. The right-side bell carries the colored "subscribed" marker. -->
						<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
							<BellRing class="mt-px size-3.5 shrink-0" />
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
					disabled={offlineGate.disabled}
					title={offlineGate.title}
					class={[
						'flex h-11 w-11 items-center justify-center rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40',
						event.user_subscription
							? 'text-primary hover:bg-primary/10'
							: 'text-muted-foreground hover:bg-accent hover:text-foreground'
					]}
					aria-label={event.user_subscription ? 'Отписаться' : 'Подписаться'}
					aria-pressed={event.user_subscription !== null}
				>
					{#if event.user_subscription}
						<BellRing class="size-5" />
					{:else}
						<Bell class="size-5" />
					{/if}
				</button>
			</div>
		</div>

		<!-- Staff management strip: broadcast actions live on their own row so they never crowd the title, and read as "changes the show for everyone" distinct from the personal bell above. -->
		{#if canManageSchedule(user)}
			<div
				class="mt-3 flex flex-wrap items-center justify-end gap-1.5 border-t border-border/50 pt-2.5"
			>
				<!-- Icon-only staff actions: 44px square tap targets keep mobile usable while the strip stays compact on dense rows. Labels live in aria-label/title. -->
				<!-- Mark-current is the hot, repeated live-show action, so it carries a primary tint while move/skip stay quiet ghosts. -->
				<!-- Hidden on skipped events: a skipped event can't go on stage (backend rejects it), so don't offer the action. Still shown when it's somehow current, to keep the unmark affordance available. -->
				{#if event.is_current || !isSkipped}
					<button
						type="button"
						onclick={askToggleCurrent}
						disabled={offlineGate.disabled}
						aria-label={currentActionLabel}
						title={offlineGate.disabled ? offlineGate.title : currentActionLabel}
						class="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors hover:bg-primary/20 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40"
					>
						{#if event.is_current}
							<XCircle class="size-5" />
						{:else}
							<Play class="size-5" />
						{/if}
					</button>
				{/if}

				<button
					type="button"
					onclick={() => (moveModal = true)}
					disabled={offlineGate.disabled}
					aria-label="Перенести"
					title={offlineGate.disabled ? offlineGate.title : 'Перенести'}
					class="inline-flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40"
				>
					<Shuffle class="size-5" />
				</button>

				<button
					type="button"
					onclick={askToggleSkip}
					disabled={offlineGate.disabled}
					aria-label={skipActionLabel}
					title={offlineGate.disabled ? offlineGate.title : skipActionLabel}
					class={[
						'inline-flex h-11 w-11 items-center justify-center rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40',
						isSkipped
							? 'text-muted-foreground hover:bg-accent hover:text-foreground'
							: 'text-destructive hover:bg-destructive/10'
					]}
				>
					{#if isSkipped}
						<Eye class="size-5" />
					{:else}
						<EyeOff class="size-5" />
					{/if}
				</button>
			</div>
		{/if}
	</div>
</div>

<!-- Mounted only while open. This card renders once per schedule row, so
	always-mounted dialogs cost four component instances — and four API clients —
	per row for something almost never opened. -->
{#if subscribeModal}
	<SubscribeModal bind:open={subscribeModal} {event} />
{/if}

{#if unsubscribeModal}
	<UnsubscribeModal bind:open={unsubscribeModal} {event} />
{/if}

{#if moveModal}
	<MoveEventModal bind:open={moveModal} {event} />
{/if}

<!-- Shared confirm dialog for the staff strip's broadcast actions. -->
{#if confirmOpen && confirmConfig}
	<ConfirmActionModal
		bind:open={confirmOpen}
		title={confirmConfig.title}
		message={confirmConfig.message}
		confirmLabel={confirmConfig.confirmLabel}
		confirmColor={confirmConfig.color}
		notifyTone={confirmConfig.notifyTone}
		onconfirm={() => void confirmConfig?.run()}
	/>
{/if}
