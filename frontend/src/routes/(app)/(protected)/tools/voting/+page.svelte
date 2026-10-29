<script lang="ts">
	import Award from '@lucide/svelte/icons/award';
	import Gift from '@lucide/svelte/icons/gift';
	import Users from '@lucide/svelte/icons/users';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';

	import type { UserBaseDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		drawVotingContestWinnerMutation,
		getVotingDashboardOptions,
		getVotingDashboardQueryKey,
		getVotingStatusQueryKey,
		listVotingNominationsQueryKey,
		setVotingTimeRangeMutation,
		updateNominationMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import FormError from '#lib/components/FormError.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Switch } from '#lib/components/ui/switch/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { fromEventDateTimeLocal, toEventDateTimeLocal } from '#lib/utils/formatters.js';

	import type { PageProps } from './$types';

	import ToolSection from '../components/ToolSection.svelte';

	let { data }: PageProps = $props();
	const toastService = getToastService();
	const queryClient = useQueryClient();

	const dashboardQuery = createQuery(() => getVotingDashboardOptions());
	let dashboard = $derived(dashboardQuery.data ?? data.dashboard);
	let nominations = $derived(dashboard.nominations);

	let votingStart = $state(untrack(() => toLocalInput(data.dashboard.voting_starts_at)));
	let votingEnd = $state(untrack(() => toLocalInput(data.dashboard.voting_ends_at)));
	const timeRangeMutation = createMutation(() => ({
		...setVotingTimeRangeMutation(),
		onSuccess: () => void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() })
	}));

	// Writable derived: a draw reports a fresher pool size until the next refetch.
	let poolSize = $derived(dashboard.contest_pool_size);
	const drawMutation = createMutation(() => drawVotingContestWinnerMutation());
	let winner = $state<UserBaseDto | null>(null);
	let hasDrawn = $state(false);
	let drawError = $state('');

	let canDraw = $derived(poolSize > 0);

	const votableMutation = createMutation(() => ({
		...updateNominationMutation(),
		onSuccess: () =>
			Promise.all([
				queryClient.invalidateQueries({ queryKey: getVotingDashboardQueryKey() }),
				queryClient.invalidateQueries({ queryKey: listVotingNominationsQueryKey() })
			])
	}));
	// Requested state per nomination ID, shown on the switch until the refetch lands.
	const pendingVotable = new SvelteMap<string, boolean>();

	async function setVotable(nominationId: string, isVotable: boolean) {
		pendingVotable.set(nominationId, isVotable);
		try {
			await votableMutation.mutateAsync({
				path: { nomination_id: nominationId },
				body: { is_votable: isVotable }
			});
		} catch (error) {
			toastService.error(error, m.voting_nomination_toggle_failed());
		} finally {
			pendingVotable.delete(nominationId);
		}
	}

	function toLocalInput(iso: string | null): string {
		if (!iso) return '';
		return toEventDateTimeLocal(iso);
	}

	function fromLocalInput(value: string): string | null {
		if (!value) return null;
		return fromEventDateTimeLocal(value);
	}

	function handleSave() {
		timeRangeMutation.mutate(
			{
				body: {
					voting_starts_at: fromLocalInput(votingStart),
					voting_ends_at: fromLocalInput(votingEnd)
				}
			},
			{
				onSuccess: () => toastService.add(m.voting_period_saved(), 'success'),
				onError: (error) => toastService.error(error, m.voting_period_save_failed())
			}
		);
	}

	function handleClear() {
		votingStart = '';
		votingEnd = '';
		handleSave();
	}

	function handleDraw() {
		drawError = '';
		drawMutation.mutate(
			{},
			{
				onSuccess: (result) => {
					poolSize = result.pool_size;
					winner = result.winner;
					hasDrawn = true;
				},
				onError: (error) => {
					drawError = getApiErrorDetail(error) ?? m.voting_draw_failed();
				}
			}
		);
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_voting() })}</title>
</svelte:head>

<SectionIntro description={m.voting_admin_description()} />

<div class="mx-auto flex w-full max-w-2xl flex-col gap-5">
	<ToolSection title={m.voting_period_title()}>
		<p class="text-sm leading-5 text-muted-foreground">
			{m.voting_period_hint()}
		</p>

		<Field.FieldGroup class="grid gap-4 sm:grid-cols-2">
			<Field.Field>
				<Field.FieldLabel for="voting-start">{m.common_start()}</Field.FieldLabel>
				<Input
					id="voting-start"
					type="datetime-local"
					bind:value={votingStart}
					disabled={timeRangeMutation.isPending}
				/>
			</Field.Field>
			<Field.Field>
				<Field.FieldLabel for="voting-end">{m.common_end()}</Field.FieldLabel>
				<Input
					id="voting-end"
					type="datetime-local"
					bind:value={votingEnd}
					disabled={timeRangeMutation.isPending}
				/>
			</Field.Field>
		</Field.FieldGroup>

		<div class="flex flex-wrap gap-2">
			<Button type="button" disabled={timeRangeMutation.isPending} onclick={handleSave}>
				{#if timeRangeMutation.isPending}
					<Spinner data-icon="inline-start" />
				{/if}
				{m.common_save()}
			</Button>
			<Button
				type="button"
				variant="outline"
				disabled={timeRangeMutation.isPending || (!votingStart && !votingEnd)}
				onclick={handleClear}
			>
				{m.common_reset()}
			</Button>
		</div>
	</ToolSection>

	<ToolSection title={m.voting_draw_title()} icon={Gift}>
		<p class="text-sm leading-5 text-muted-foreground">
			{m.voting_draw_hint()}
		</p>

		<div class="flex items-center gap-2 text-sm text-muted-foreground">
			<Users class="size-4" aria-hidden="true" />
			<span>
				{m.voting_draw_pool({ count: poolSize })}
			</span>
		</div>

		<FormError message={drawError} />

		{#if hasDrawn}
			<div aria-live="polite" role="status">
				{#if winner}
					<div class="flex items-center gap-3 rounded-xl bg-primary/10 p-3">
						<Award class="size-6 shrink-0 text-primary" aria-hidden="true" />
						<div class="min-w-0">
							<p class="text-xs text-muted-foreground">{m.voting_winner()}</p>
							<p class="text-base font-semibold wrap-anywhere text-foreground">
								{winner.username}
							</p>
						</div>
					</div>
				{:else}
					<p class="text-sm text-muted-foreground">
						{m.voting_draw_empty()}
					</p>
				{/if}
			</div>
		{/if}

		<Button
			type="button"
			class="w-full sm:w-auto"
			disabled={drawMutation.isPending || !canDraw}
			onclick={handleDraw}
		>
			{#if drawMutation.isPending}
				<Spinner data-icon="inline-start" />
				{m.voting_drawing()}
			{:else}
				{hasDrawn ? m.voting_draw_again() : m.voting_draw_action()}
			{/if}
		</Button>
		{#if !canDraw}
			<p class="text-xs text-muted-foreground">
				{m.voting_draw_disabled_hint()}
			</p>
		{/if}
	</ToolSection>

	<ToolSection title={m.voting_nominations_admin_title()} icon={Award}>
		{#if nominations.length > 0}
			<p class="text-sm leading-5 text-muted-foreground">
				{m.voting_nominations_admin_hint()}
			</p>
			<ul class="flex flex-col gap-3">
				{#each nominations as nomination (nomination.id)}
					{const switchId = $derived(`nomination-votable-${nomination.id}`)}
					<li class="border-b border-border pb-3 last:border-0 last:pb-0">
						<div class="flex min-h-11 items-center justify-between gap-3">
							<label for={switchId} class="text-sm font-medium text-foreground">
								{nomination.title}
							</label>
							<Switch
								id={switchId}
								bind:checked={
									() => pendingVotable.get(nomination.id) ?? nomination.is_votable,
									(isVotable: boolean) => void setVotable(nomination.id, isVotable)
								}
								disabled={pendingVotable.has(nomination.id)}
							/>
						</div>
						{#if nomination.leader}
							<div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
								<span class="text-sm text-muted-foreground">
									{nomination.leader.title}
								</span>
								<Badge>
									{m.voting_leader_votes({
										count: nomination.leader.votes_count,
										total: nomination.total_votes
									})}
								</Badge>
							</div>
						{:else}
							<p class="mt-1 text-xs text-muted-foreground">{m.voting_no_votes()}</p>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<EmptyState
				icon={Users}
				title={m.voting_no_nominations_title()}
				message={m.voting_no_nominations_message()}
			/>
		{/if}
	</ToolSection>
</div>
