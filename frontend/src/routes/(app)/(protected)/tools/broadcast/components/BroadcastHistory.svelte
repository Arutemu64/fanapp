<script lang="ts">
	import { createInfiniteQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { MailingDto, MailingStatus, UserRole } from '#lib/api/generated/index.js';

	import {
		cancelMailingMutation,
		listBroadcastsInfiniteOptions,
		listBroadcastsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Badge, type BadgeVariant } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { BROADCAST_PAGE_SIZE } from '#lib/constants/notifications.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { formatFestivalDateTime } from '#lib/utils/formatters.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const cancelMutation = createMutation(() => ({
		...cancelMailingMutation(),
		onSuccess: () => toastService.add(m.broadcast_cancelled(), 'success'),
		onError: (error) => toastService.error(error, m.broadcast_cancel_failed()),
		onSettled: () => queryClient.invalidateQueries({ queryKey: listBroadcastsQueryKey() })
	}));
	let cancellingId = $derived(
		cancelMutation.isPending ? cancelMutation.variables.path.mailing_id : null
	);

	const mailingsQuery = createInfiniteQuery(() => ({
		...listBroadcastsInfiniteOptions({ query: { limit: BROADCAST_PAGE_SIZE } }),
		initialPageParam: {},
		getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
	}));

	let mailings = $derived(mailingsQuery.data?.pages.flatMap((page) => page.mailings) ?? []);

	const STATUS_LABELS: Record<MailingStatus, string> = {
		pending: m.status_queued(),
		finished: m.mailing_status_finished(),
		cancelled: m.mailing_status_cancelled(),
		failed: m.status_error()
	};

	const STATUS_VARIANTS: Record<MailingStatus, BadgeVariant> = {
		pending: 'outline',
		finished: 'secondary',
		cancelled: 'outline',
		failed: 'destructive'
	};

	const ROLE_LABELS: Record<UserRole, string> = {
		visitor: m.audience_visitors(),
		participant: m.audience_participants(),
		volunteer: m.audience_volunteers(),
		organizer: m.audience_organizers()
	};

	function isCancellable(status: MailingStatus): boolean {
		return status !== 'cancelled';
	}

	function rolesLabel(roles: UserRole[] | null): string {
		if (!roles || roles.length === 0) return '';
		return roles.map((role) => ROLE_LABELS[role]).join(', ');
	}

	let recallOpen = $state(false);
	let mailingToRecall = $state.raw<MailingDto | null>(null);

	function askToRecall(mailing: MailingDto) {
		mailingToRecall = mailing;
		recallOpen = true;
	}

	function handleConfirmRecall() {
		if (!mailingToRecall) {
			return;
		}
		cancelMutation.mutate({ path: { mailing_id: mailingToRecall.id } });
		recallOpen = false;
	}

	let listElement = $state<HTMLElement | null>(null);
</script>

<section class="mx-auto w-full max-w-2xl">
	<h2 class="mb-3 text-section text-foreground">
		{m.broadcast_history_title()}
	</h2>

	{#if mailingsQuery.data === undefined}
		{#if mailingsQuery.isError}
			<EmptyState message={m.broadcast_history_load_failed()} />
		{:else}
			<SectionSpinner />
		{/if}
	{:else if mailings.length === 0}
		<EmptyState message={m.broadcast_history_empty()} />
	{:else}
		<MenuGroup class="divide-y divide-border" bind:ref={listElement}>
			{#each mailings as mailing (mailing.id)}
				<div class="p-4">
					<div class="flex flex-col gap-2">
						<div class="flex items-center justify-between gap-2">
							<Badge variant={STATUS_VARIANTS[mailing.status]}>
								{STATUS_LABELS[mailing.status]}
							</Badge>
							<span class="text-xs text-muted-foreground">
								{formatFestivalDateTime(mailing.created_at)}
							</span>
						</div>

						{#if mailing.body}
							<p class="line-clamp-2 text-sm wrap-break-word whitespace-pre-line">
								{mailing.body}
							</p>
						{/if}

						<div
							class="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground"
						>
							<span>
								{rolesLabel(mailing.roles)}
								{#if mailing.total_count > 0}
									{m.broadcast_recipients({ count: mailing.total_count })}
								{/if}
							</span>
							{#if isCancellable(mailing.status)}
								<Button
									variant="outline"
									size="sm"
									class="min-h-9"
									disabled={cancellingId === mailing.id}
									onclick={() => askToRecall(mailing)}
								>
									{#if cancellingId === mailing.id}
										<Spinner data-icon="inline-start" />
									{/if}
									{m.broadcast_recall()}
								</Button>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</MenuGroup>

		<LoadMoreButton
			query={mailingsQuery}
			list={listElement}
			errorMessage={m.broadcast_history_load_failed_toast()}
		/>
	{/if}
</section>

<AlertDialog.Root bind:open={recallOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{m.broadcast_recall_title()}</AlertDialog.Title>
			<AlertDialog.Description>{m.broadcast_recall_description()}</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>{m.broadcast_recall_keep()}</AlertDialog.Cancel>
			<AlertDialog.Action variant="destructive" onclick={handleConfirmRecall}>
				{m.broadcast_recall_confirm()}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
