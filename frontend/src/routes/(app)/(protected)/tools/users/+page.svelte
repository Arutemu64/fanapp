<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { Search as SearchIcon, X } from '@lucide/svelte';
	import { createInfiniteQuery, keepPreviousData } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';

	import type { ListUsersData } from '#lib/api/generated/index.js';

	import { listUsersInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { USER_ROLES, USERS_PAGE_SIZE } from '#lib/constants/users.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { queryView } from '#lib/utils/queryView.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	import SectionSpinner from '../../../components/SectionSpinner.svelte';
	import UserRow from './components/UserRow.svelte';
	import { buildUserFiltersQuery, parseUserFilters, type UserFilters } from './userFilters';

	const toastService = getToastService();

	let filters = $derived(parseUserFilters(page.url.searchParams));
	let hasActiveFilters = $derived(
		filters.search !== '' || filters.role !== null || filters.hasTicket !== null
	);

	// Local, editable mirror of the URL search term so the input stays responsive
	// while the request waits for a short debounce (below). Seeded once (untrack);
	// typing then drives navigation.
	let searchValue = $state(untrack(() => filters.search));

	const usersQuery = createInfiniteQuery(() => {
		const query: NonNullable<ListUsersData['query']> = { limit: USERS_PAGE_SIZE };
		if (filters.search) query.search = filters.search;
		if (filters.role) query.role = filters.role;
		if (filters.hasTicket !== null) query.has_ticket = filters.hasTicket;
		return {
			...listUsersInfiniteOptions({ query }),
			// An object page param is request overrides to hey-api, a string the
			// cursor: an empty object asks for the first page.
			initialPageParam: {},
			getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
			// Keep the current list on screen while a new filter loads, instead of
			// flashing a spinner on every keystroke.
			placeholderData: keepPreviousData
		};
	});

	let users = $derived(usersQuery.data?.pages.flatMap((usersPage) => usersPage.users) ?? []);
	let total = $derived(usersQuery.data?.pages[0]?.total ?? 0);
	let usersView = $derived(
		queryView(usersQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.users_load_failed()
		})
	);
	let resultsSummary = $derived(m.users_count({ count: total }));

	function applyFilters(next: UserFilters) {
		// `replace` keeps the history stack from filling with every intermediate
		// filter; `reset: false` leaves scroll and focus alone, so the keyboard stays
		// open on the search field.
		void goto(`${resolve('tools/users')}${buildUserFiltersQuery(next)}`, {
			replace: true,
			reset: false
		});
	}

	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	function onSearchInput(value: string) {
		clearTimeout(searchTimer);
		// Debounce so a request fires once the user pauses, not on every keystroke.
		searchTimer = setTimeout(() => applyFilters({ ...filters, search: value }), 300);
	}

	function clearSearch() {
		clearTimeout(searchTimer);
		searchValue = '';
		applyFilters({ ...filters, search: '' });
	}

	function resetFilters() {
		clearTimeout(searchTimer);
		searchValue = '';
		applyFilters({ search: '', role: null, hasTicket: null });
	}

	const ALL = 'all';
	const ticketOptions = [
		{ value: ALL, label: m.users_filter_ticket_any() },
		{ value: 'yes', label: m.users_filter_with_ticket() },
		{ value: 'no', label: m.users_filter_without_ticket() }
	];

	let roleValue = $derived(filters.role ?? ALL);
	let roleLabel = $derived(filters.role ? getRoleLabel(filters.role) : m.users_filter_role_all());
	let ticketValue = $derived.by(() => {
		if (filters.hasTicket === null) return ALL;
		return filters.hasTicket ? 'yes' : 'no';
	});
	let ticketLabel = $derived(
		ticketOptions.find((option) => option.value === ticketValue)?.label ?? ''
	);

	function onRoleChange(value: string) {
		const role = USER_ROLES.find((candidate) => candidate === value) ?? null;
		applyFilters({ ...filters, role });
	}

	function onTicketChange(value: string) {
		let hasTicket: boolean | null = null;
		if (value === 'yes') hasTicket = true;
		if (value === 'no') hasTicket = false;
		applyFilters({ ...filters, hasTicket });
	}

	async function loadMore() {
		const result = await usersQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(m.users_load_failed(), 'error');
		}
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_users() })}</title>
</svelte:head>

<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
	<SectionIntro description={m.users_description()} />

	<div class="flex flex-col gap-3">
		<div class="relative flex items-center">
			<SearchIcon
				class="pointer-events-none absolute left-3 size-4 text-muted-foreground"
				aria-hidden="true"
			/>
			<Input
				type="search"
				bind:value={searchValue}
				placeholder={m.users_search_placeholder()}
				aria-label={m.users_search_label()}
				autocomplete="off"
				autocapitalize="off"
				spellcheck={false}
				enterkeyhint="search"
				class="pr-10 pl-9 [&::-webkit-search-cancel-button]:hidden"
				oninput={() => onSearchInput(searchValue)}
			/>
			{#if searchValue}
				<button
					type="button"
					class="absolute right-0 flex size-11 items-center justify-center text-muted-foreground hover:text-foreground"
					onclick={clearSearch}
					aria-label={m.common_clear_search()}
				>
					<X class="size-4" />
				</button>
			{/if}
		</div>

		<!-- Two selects side by side rather than rows of chips: four roles and three
		     ticket states fit one line on a phone, and the current choice stays
		     readable on the trigger. -->
		<div class="grid grid-cols-2 gap-2">
			<Select.Root type="single" value={roleValue} onValueChange={onRoleChange}>
				<Select.Trigger class="w-full" aria-label={m.common_role()}>{roleLabel}</Select.Trigger>
				<Select.Content>
					<Select.Item value={ALL} label={m.users_filter_role_all()}
						>{m.users_filter_role_all()}</Select.Item
					>
					{#each USER_ROLES as role (role)}
						<Select.Item value={role} label={getRoleLabel(role)}>
							{getRoleLabel(role)}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<Select.Root type="single" value={ticketValue} onValueChange={onTicketChange}>
				<Select.Trigger class="w-full" aria-label={m.ticket_title()}>{ticketLabel}</Select.Trigger>
				<Select.Content>
					{#each ticketOptions as option (option.value)}
						<Select.Item value={option.value} label={option.label}>{option.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		<div class="flex min-h-9 items-center justify-between gap-3">
			<p class="text-xs text-muted-foreground" aria-live="polite" role="status">
				{usersQuery.data ? resultsSummary : ''}
			</p>
			{#if hasActiveFilters}
				<Button variant="ghost" size="sm" onclick={resetFilters}>{m.common_reset()}</Button>
			{/if}
		</div>
	</div>

	<QueryState view={usersView}>
		{#snippet loading()}
			<SectionSpinner />
		{/snippet}

		{#snippet ready()}
			{#if users.length === 0}
				<EmptyState
					title={m.users_empty_title()}
					message={hasActiveFilters ? m.users_empty_filtered() : m.users_empty()}
				/>
			{:else}
				<div class={['transition-opacity', usersQuery.isPlaceholderData && 'opacity-60']}>
					<MenuGroup class="divide-y divide-border">
						{#each users as listedUser (listedUser.id)}
							<UserRow user={listedUser} />
						{/each}
					</MenuGroup>

					{#if usersQuery.hasNextPage}
						<LoadMoreButton
							loading={usersQuery.isFetchingNextPage}
							busy={usersQuery.isFetching}
							onclick={loadMore}
						/>
					{/if}
				</div>
			{/if}
		{/snippet}
	</QueryState>
</div>
