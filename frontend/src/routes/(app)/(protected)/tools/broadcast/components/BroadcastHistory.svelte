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

	// Toasts live on the mutation, not on each `mutate` call: a second row can be
	// cancelled before the first answers, and `mutate` only calls back for the latest.
	const cancelMutation = createMutation(() => ({
		...cancelMailingMutation(),
		onSuccess: () => toastService.add(m.broadcast_cancelled(), 'success'),
		onError: (error) => toastService.error(error, m.broadcast_cancel_failed()),
		// Refresh from the server whether it succeeded or raced with another
		// change, so the row reflects the real state.
		onSettled: () => queryClient.invalidateQueries({ queryKey: listBroadcastsQueryKey() })
	}));
	let cancellingId = $derived(
		cancelMutation.isPending ? cancelMutation.variables?.path.mailing_id : null
	);

	const mailingsQuery = createInfiniteQuery(() => ({
		...listBroadcastsInfiniteOptions({ query: { limit: BROADCAST_PAGE_SIZE } }),
		// An object page param is request overrides to hey-api, a string the cursor:
		// an empty object asks for the first page.
		initialPageParam: {},
		getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
	}));

	let mailings = $derived(mailingsQuery.data?.pages.flatMap((page) => page.mailings) ?? []);

	async function loadMore() {
		const result = await mailingsQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(m.broadcast_history_load_failed_toast(), 'error');
		}
	}

	const STATUS_LABELS: Record<MailingStatus, string> = {
		pending: m.status_queued(),
		sending: m.mailing_status_sending(),
		finished: m.mailing_status_finished(),
		cancelled: m.mailing_status_cancelled(),
		failed: m.status_error()
	};

	const STATUS_VARIANTS: Record<MailingStatus, BadgeVariant> = {
		pending: 'outline',
		sending: 'default',
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
		return status === 'pending' || status === 'sending';
	}

	function rolesLabel(roles: UserRole[] | null): string {
		if (!roles || roles.length === 0) return '';
		return roles.map((role) => ROLE_LABELS[role]).join(', ');
	}

	function cancel(mailing: MailingDto) {
		cancelMutation.mutate({ path: { mailing_id: mailing.id } });
	}
</script>

<section class="mx-auto w-full max-w-2xl">
	<h2 class="mb-3 text-section text-foreground">
		{m.broadcast_history_title()}
	</h2>

	{#if mailingsQuery.data === undefined}
		<!-- Best-effort: a history that fails to load must not block the composer
		     above it, so it degrades to a line rather than an error page. -->
		{#if mailingsQuery.isError}
			<EmptyState message={m.broadcast_history_load_failed()} />
		{:else}
			<SectionSpinner />
		{/if}
	{:else if mailings.length === 0}
		<EmptyState message={m.broadcast_history_empty()} />
	{:else}
		<!-- One divided list, not a card per mailing: the entries are all the same
		     shape, so a list scans faster and fits more on a phone screen. -->
		<MenuGroup class="divide-y divide-border">
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
									{m.broadcast_progress_suffix({
										sent_count: mailing.sent_count,
										total_count: mailing.total_count
									})}
								{/if}
							</span>
							{#if isCancellable(mailing.status)}
								<Button
									variant="outline"
									size="sm"
									class="min-h-9"
									disabled={cancellingId === mailing.id}
									onclick={() => cancel(mailing)}
								>
									{#if cancellingId === mailing.id}
										<Spinner data-icon="inline-start" />
									{/if}
									{m.common_revert()}
								</Button>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</MenuGroup>

		{#if mailingsQuery.hasNextPage}
			<LoadMoreButton
				loading={mailingsQuery.isFetchingNextPage}
				busy={mailingsQuery.isFetching}
				onclick={loadMore}
			/>
		{/if}
	{/if}
</section>
