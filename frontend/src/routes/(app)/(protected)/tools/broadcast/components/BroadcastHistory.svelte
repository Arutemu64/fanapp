<script lang="ts">
	import type { MailingDto, MailingStatus, UserRole } from '$lib/api/generated';

	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { cancelMailing } from '$lib/api/generated';
	import {
		listBroadcastsInfiniteOptions,
		listBroadcastsQueryKey
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { offsetPagination } from '$lib/api/queries';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import { BROADCAST_PAGE_SIZE } from '$lib/constants/notifications';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { formatFestivalDateTime } from '$lib/utils/formatters';
	import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';

	const toastService = getToastService();
	const queryClient = useQueryClient();

	let cancellingId = $state<string | null>(null);

	const feedQuery = createInfiniteQuery(() => ({
		...listBroadcastsInfiniteOptions({ query: { limit: BROADCAST_PAGE_SIZE } }),
		...offsetPagination(BROADCAST_PAGE_SIZE, 'mailings')
	}));

	let mailings = $derived(feedQuery.data?.pages.flatMap((page) => page.mailings) ?? []);

	$effect(() => {
		if (feedQuery.isError) {
			toastService.error('Не удалось загрузить рассылки');
		}
	});

	const STATUS_LABELS: Record<MailingStatus, string> = {
		pending: 'В очереди',
		sending: 'Отправляется',
		finished: 'Отправлена',
		cancelled: 'Отменена',
		failed: 'Ошибка'
	};

	const STATUS_VARIANTS: Record<MailingStatus, BadgeVariant> = {
		pending: 'outline',
		sending: 'default',
		finished: 'secondary',
		cancelled: 'outline',
		failed: 'destructive'
	};

	const ROLE_LABELS: Record<UserRole, string> = {
		visitor: 'Зрители',
		participant: 'Участники',
		helper: 'Волонтёры',
		org: 'Организаторы'
	};

	function isCancellable(status: MailingStatus): boolean {
		return status === 'pending' || status === 'sending';
	}

	function rolesLabel(roles: UserRole[] | null): string {
		if (!roles || roles.length === 0) return '';
		return roles.map((role) => ROLE_LABELS[role]).join(', ');
	}

	async function cancel(mailing: MailingDto): Promise<void> {
		cancellingId = mailing.id;
		try {
			const { error, response } = await cancelMailing({
				client,
				path: { mailing_id: mailing.id }
			});
			if (error || !response?.ok) {
				toastService.error(getApiErrorDetail(error) ?? 'Не удалось отменить рассылку');
			} else {
				toastService.add('Рассылка отменена', 'success');
			}
			// Refresh from the server whether it succeeded or raced with another
			// change, so the row reflects the real state. Every loaded page refetches,
			// so a cancelled mailing updates in place rather than only on page one.
			await queryClient.invalidateQueries({ queryKey: listBroadcastsQueryKey() });
		} finally {
			cancellingId = null;
		}
	}
</script>

<section class="mx-auto w-full max-w-2xl">
	<h2 class="mb-3 text-lg font-bold">История рассылок</h2>

	{#if mailings.length === 0}
		<EmptyState message="Пока ничего не отправлено" />
	{:else}
		<div class="flex flex-col gap-3">
			{#each mailings as mailing (mailing.id)}
				<Card.Root class="rounded-xl p-4">
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
							<p class="line-clamp-2 text-sm break-words whitespace-pre-line">
								{mailing.body}
							</p>
						{/if}

						<div
							class="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground"
						>
							<span>
								{rolesLabel(mailing.roles)}
								{#if mailing.total_count > 0}
									· отправлено {mailing.sent_count} из {mailing.total_count}
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
									Отменить
								</Button>
							{/if}
						</div>
					</div>
				</Card.Root>
			{/each}
		</div>

		{#if feedQuery.hasNextPage}
			<LoadMoreButton
				loading={feedQuery.isFetchingNextPage}
				onclick={() => feedQuery.fetchNextPage()}
			/>
		{/if}
	{/if}
</section>
