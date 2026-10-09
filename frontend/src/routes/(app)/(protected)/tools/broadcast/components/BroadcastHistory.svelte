<script lang="ts">
	import { invalidate } from '$app/navigation';

	import type { MailingDto, MailingStatus, UserRole } from '#lib/api/generated/index.js';

	import { cancelMailing, listBroadcasts } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import { Badge, type BadgeVariant } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import {
		BROADCAST_PAGE_REQUEST_LIMIT,
		BROADCAST_PAGE_SIZE
	} from '#lib/constants/notifications.js';
	import { PaginatedFeed } from '#lib/services/feed.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { formatFestivalDateTime } from '#lib/utils/formatters.js';

	interface Props {
		initialMailings: Array<MailingDto>;
		initialHasMore: boolean;
	}

	let { initialMailings, initialHasMore }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();

	let cancellingId = $state<string | null>(null);

	const feed = new PaginatedFeed<MailingDto>({
		pageSize: BROADCAST_PAGE_SIZE,
		requestLimit: BROADCAST_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialMailings,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await listBroadcasts({
				client,
				query: { limit, offset }
			});
			return error || !data ? null : data.mailings;
		},
		onError: () => toastService.add('Не удалось загрузить рассылки', 'error')
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
				toastService.error(error, 'Не удалось отменить рассылку');
			} else {
				toastService.add('Рассылка отменена', 'success');
			}
			// Refresh from the server whether it succeeded or raced with another
			// change, so the row reflects the real state (the page remounts this
			// feed with the fresh first page).
			await invalidate('app:broadcasts');
		} finally {
			cancellingId = null;
		}
	}
</script>

<section class="mx-auto w-full max-w-2xl">
	<h2 class="mb-3 text-base font-semibold text-foreground sm:text-lg">История рассылок</h2>

	{#if feed.items.length === 0}
		<EmptyState message="Пока ничего не отправлено" />
	{:else}
		<!-- One divided list, not a card per mailing: the entries are all the same
		     shape, so a list scans faster and fits more on a phone screen. -->
		<MenuGroup class="divide-y divide-border">
			{#each feed.items as mailing (mailing.id)}
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
				</div>
			{/each}
		</MenuGroup>

		{#if feed.hasMore}
			<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
		{/if}
	{/if}
</section>
