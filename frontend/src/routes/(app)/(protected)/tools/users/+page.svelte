<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import {
		ArrowLeft,
		ArrowRight,
		ChevronRight,
		Search as SearchIcon,
		Users,
		X
	} from '@lucide/svelte';
	import { untrack } from 'svelte';

	import EmptyState from '#lib/components/EmptyState.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as Item from '#lib/components/ui/item/index.js';
	import { USERS_PAGE_SIZE } from '#lib/constants/users.js';
	import { getAvatarInitials, getRoleLabel } from '#lib/utils/users.js';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Local, editable mirror of the URL search term so the input stays responsive
	// while the real query runs server-side after a short debounce (below).
	// Seeded once (untrack) from the initial term; typing then drives navigation.
	let searchValue = $state(untrack(() => data.search));

	let totalPages = $derived(Math.max(1, Math.ceil(data.total / USERS_PAGE_SIZE)));
	let rangeStart = $derived(data.total === 0 ? 0 : (data.page - 1) * USERS_PAGE_SIZE + 1);
	let rangeEnd = $derived(Math.min(data.page * USERS_PAGE_SIZE, data.total));

	function buildQuery(page: number, search: string): string {
		const parts: string[] = [];
		if (search) {
			parts.push(`q=${encodeURIComponent(search)}`);
		}
		if (page > 1) {
			parts.push(`page=${page}`);
		}
		const query = parts.join('&');
		return query ? `?${query}` : '';
	}

	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	function onSearchInput(value: string) {
		clearTimeout(searchTimer);
		// Debounce so a new request fires once the user pauses, not on every
		// keystroke. A search always resets to the first page. `replace` keeps
		// the history stack from filling with every intermediate query.
		searchTimer = setTimeout(() => {
			void goto(`${resolve('tools/users')}${buildQuery(1, value.trim())}`, {
				replace: true,
				reset: false
			});
		}, 300);
	}

	let searchInput = $state<HTMLInputElement | null>(null);

	// Focus goes back to the field, not to <body> as the button unmounts.
	function clearSearch() {
		searchValue = '';
		onSearchInput('');
		searchInput?.focus();
	}

	function goToPage(page: number) {
		void goto(`${resolve('tools/users')}${buildQuery(page, data.search)}`);
	}
</script>

<svelte:head>
	<title>Пользователи · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Список всех пользователей. Найди по имени или почте и открой карточку."
/>

<div class="flex flex-col gap-4">
	<!-- type="search" brings the phone keyboard's search key; the label is for screen
	     readers, as the placeholder vanishes once typing starts. -->
	<div class="relative flex items-center">
		<SearchIcon
			class="pointer-events-none absolute left-3 size-4 text-muted-foreground"
			aria-hidden="true"
		/>
		<Input
			bind:ref={searchInput}
			bind:value={searchValue}
			type="search"
			name="users_search"
			aria-label="Поиск пользователей"
			placeholder="Поиск по имени или почте"
			autocomplete="off"
			spellcheck={false}
			enterkeyhint="search"
			class="pr-11 pl-9 [&::-webkit-search-cancel-button]:hidden"
			oninput={() => onSearchInput(searchValue)}
		/>
		{#if searchValue}
			<!-- Full input height, so the clear target meets the 44px tap size. -->
			<Button
				variant="ghost"
				size="icon"
				class="absolute right-0 text-muted-foreground"
				onclick={clearSearch}
				aria-label="Очистить поиск"
			>
				<X aria-hidden="true" />
			</Button>
		{/if}
	</div>

	{#if data.users.length > 0}
		<!-- Rows, not a table: four columns on a phone scroll sideways, and the list
		     only needs to get the organiser to the right card
		     (https://uxmovement.com/mobile/stacked-lists-the-best-pattern-to-display-mobile-tables/). -->
		<MenuGroup>
			<ul class="divide-y divide-border">
				{#each data.users as listedUser (listedUser.id)}
					<li>
						<Item.Root class="rounded-none">
							{#snippet child({ props })}
								<a href={resolve(`tools/users/${listedUser.id}`)} {...props}>
									<Item.Media
										class="size-9 rounded-full bg-muted text-sm font-semibold text-muted-foreground"
									>
										<span aria-hidden="true">{getAvatarInitials(listedUser.username)}</span>
									</Item.Media>
									<Item.Content class="min-w-0">
										<Item.Title class="text-base">{listedUser.username}</Item.Title>
										<Item.Description class="truncate">
											{getRoleLabel(listedUser.role)} · {listedUser.email ?? 'без почты'}
										</Item.Description>
									</Item.Content>
									<Item.Actions>
										<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
									</Item.Actions>
								</a>
							{/snippet}
						</Item.Root>
					</li>
				{/each}
			</ul>
		</MenuGroup>

		<nav
			aria-label="Страницы списка"
			class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
		>
			<p class="text-xs text-muted-foreground">
				Показаны {rangeStart}–{rangeEnd} из {data.total}
			</p>
			<div class="flex items-center justify-center gap-2">
				<Button
					variant="outline"
					size="sm"
					disabled={data.page <= 1}
					onclick={() => goToPage(data.page - 1)}
				>
					<ArrowLeft aria-hidden="true" data-icon="inline-start" />
					Назад
				</Button>
				<span class="text-xs text-muted-foreground">
					{data.page} / {totalPages}
				</span>
				<Button
					variant="outline"
					size="sm"
					disabled={data.page >= totalPages}
					onclick={() => goToPage(data.page + 1)}
				>
					Вперёд
					<ArrowRight aria-hidden="true" data-icon="inline-end" />
				</Button>
			</div>
		</nav>
	{:else}
		<EmptyState
			icon={Users}
			title="Никого не нашлось"
			message={data.search ? 'Попробуй изменить запрос.' : 'Пользователей пока нет.'}
		/>
	{/if}
</div>
