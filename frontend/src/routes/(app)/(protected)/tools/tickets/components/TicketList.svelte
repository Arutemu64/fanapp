<script lang="ts">
	import { resolve } from '$app/paths';
	import { createInfiniteQuery, keepPreviousData } from '@tanstack/svelte-query';

	import type { ListTicketsData } from '#lib/api/generated/index.js';

	import { listTicketsInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SearchInput from '#lib/components/SearchInput.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';

	interface Props {
		/** Linked usernames open the user page only for someone who may read it. */
		canOpenUsers: boolean;
	}

	let { canOpenUsers }: Props = $props();

	// Rows per page, loaded with "Показать ещё" like the user directory.
	const TICKETS_PAGE_SIZE = 20;

	let searchValue = $state('');
	// The term the query runs with, trailing the input by a short debounce.
	let search = $state('');

	const ticketsQuery = createInfiniteQuery(() => {
		const query: NonNullable<ListTicketsData['query']> = { limit: TICKETS_PAGE_SIZE };
		if (search) query.search = search;
		return {
			...listTicketsInfiniteOptions({ query }),
			// An object page param is request overrides to hey-api, a string the
			// cursor: an empty object asks for the first page.
			initialPageParam: {},
			getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
			placeholderData: keepPreviousData
		};
	});

	let tickets = $derived(
		ticketsQuery.data?.pages.flatMap((ticketsPage) => ticketsPage.tickets) ?? []
	);
	let total = $derived(ticketsQuery.data?.pages[0]?.total ?? 0);
	let ticketsView = $derived(
		queryView(ticketsQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.tickets_load_failed()
		})
	);

	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	function onSearchInput() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => (search = searchValue.trim()), 300);
	}

	function clearSearch() {
		clearTimeout(searchTimer);
		searchValue = '';
		search = '';
	}

	let listElement = $state<HTMLElement | null>(null);
</script>

<div class="flex flex-col gap-3">
	<SearchInput
		bind:value={searchValue}
		label={m.tickets_search_label()}
		placeholder={m.tickets_search_placeholder()}
		oninput={onSearchInput}
		onclear={clearSearch}
	/>

	<p class="min-h-4 text-xs text-muted-foreground" aria-live="polite" role="status">
		{ticketsQuery.data ? m.tickets_count({ count: total }) : ''}
	</p>

	<QueryState view={ticketsView}>
		{#snippet loading()}
			<SectionSpinner />
		{/snippet}

		{#snippet ready()}
			{#if tickets.length === 0}
				<EmptyState
					title={m.tickets_empty_title()}
					message={search ? m.tickets_empty_filtered() : m.tickets_empty()}
				/>
			{:else}
				<div class={['transition-opacity', ticketsQuery.isPlaceholderData && 'opacity-60']}>
					<MenuGroup class="divide-y divide-border" bind:ref={listElement}>
						{#each tickets as ticket (ticket.id)}
							<div class="flex min-h-16 flex-col justify-center gap-1 px-3 py-2.5 sm:px-4">
								<div class="flex min-w-0 flex-wrap items-center gap-2">
									<span class="min-w-0 font-mono text-sm wrap-anywhere text-foreground">
										{ticket.barcode}
									</span>
									<Badge variant="secondary" class="shrink-0">{getRoleLabel(ticket.role)}</Badge>
									{#if ticket.revoked_at}
										<Badge variant="destructive" class="shrink-0">{m.tickets_revoked()}</Badge>
									{/if}
								</div>
								<div class="flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
									{#if ticket.used_by && canOpenUsers}
										<a
											href={resolve(`tools/users/${ticket.used_by.id}`)}
											class="truncate text-primary underline-offset-4 hover:underline"
										>
											{ticket.used_by.username}
										</a>
									{:else if ticket.used_by}
										<span class="truncate text-foreground">{ticket.used_by.username}</span>
									{:else}
										<span>{m.tickets_not_linked()}</span>
									{/if}
									<span aria-hidden="true">·</span>
									<span class="shrink-0">
										{ticket.from_ticketscloud
											? m.tickets_source_tcloud()
											: m.tickets_source_generated()}
									</span>
								</div>
							</div>
						{/each}
					</MenuGroup>

					<LoadMoreButton
						query={ticketsQuery}
						list={listElement}
						errorMessage={m.tickets_load_failed()}
					/>
				</div>
			{/if}
		{/snippet}
	</QueryState>
</div>
