<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { USERS_PAGE_SIZE } from '$lib/constants/users';
	import { getRoleLabel } from '$lib/utils/users';
	import { ArrowLeft, ArrowRight, Search as SearchIcon, Users, X } from '@lucide/svelte';
	import { untrack } from 'svelte';

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
		// keystroke. A search always resets to the first page. replaceState keeps
		// the history stack from filling with every intermediate query.
		searchTimer = setTimeout(() => {
			// eslint-disable-next-line svelte/no-navigation-without-resolve
			void goto(`${resolve('/tools/users')}${buildQuery(1, value.trim())}`, {
				replaceState: true,
				keepFocus: true
			});
		}, 300);
	}

	function goToPage(page: number) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		void goto(`${resolve('/tools/users')}${buildQuery(page, data.search)}`);
	}
</script>

<svelte:head>
	<title>Пользователи · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro
	description="Список всех пользователей. Найди по имени или почте и открой карточку."
/>

<div class="mx-auto flex w-full max-w-3xl flex-col gap-4">
	<div class="relative flex items-center">
		<SearchIcon class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
		<Input
			bind:value={searchValue}
			placeholder="Поиск по имени или почте"
			class="pr-8 pl-9"
			oninput={() => onSearchInput(searchValue)}
		/>
		{#if searchValue}
			<button
				type="button"
				class="absolute right-2 text-muted-foreground hover:text-foreground"
				onclick={() => {
					searchValue = '';
					onSearchInput('');
				}}
				aria-label="Очистить поиск"
			>
				<X class="size-4" />
			</button>
		{/if}
	</div>

	{#if data.users.length > 0}
		<div class="relative w-full overflow-x-auto rounded-lg border border-border">
			<table class="w-full text-left text-sm">
				<thead
					class="border-b border-border bg-muted/50 text-xs font-medium text-muted-foreground uppercase"
				>
					<tr>
						<th class="px-4 py-3">Имя</th>
						<th class="px-4 py-3">Почта</th>
						<th class="px-4 py-3">Билет</th>
						<th class="px-4 py-3">Роль</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-border">
					{#each data.users as listedUser (listedUser.id)}
						<tr class="transition-colors hover:bg-muted/50">
							<td class="px-4 py-3 font-medium">
								<!-- The username is the link to the detail page: a real anchor
								     keeps the row reachable and openable by keyboard. -->
								<a
									href={resolve(`/tools/users/${listedUser.id}`)}
									class="text-primary hover:underline"
								>
									{listedUser.username}
								</a>
							</td>
							<td class="px-4 py-3 text-muted-foreground">
								{listedUser.email ?? '—'}
							</td>
							<td class="px-4 py-3 font-mono text-xs text-muted-foreground">
								{listedUser.ticket_number ?? '—'}
							</td>
							<td class="px-4 py-3">
								<Badge variant="secondary">
									{getRoleLabel(listedUser.role)}
								</Badge>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
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
		</div>
	{:else}
		<EmptyState
			icon={Users}
			title="Никого не нашлось"
			message={data.search ? 'Попробуй изменить запрос.' : 'Пользователей пока нет.'}
		/>
	{/if}
</div>
