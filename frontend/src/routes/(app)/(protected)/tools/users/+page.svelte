<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { USERS_PAGE_SIZE } from '$lib/constants/users';
	import { getRoleColor, getRoleLabel } from '$lib/utils/users';
	import {
		Badge,
		Button,
		Search,
		Table,
		TableBody,
		TableBodyCell,
		TableBodyRow,
		TableHead,
		TableHeadCell
	} from 'flowbite-svelte';
	import { ArrowLeftOutline, ArrowRightOutline, UsersGroupOutline } from 'flowbite-svelte-icons';
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

	function buildUrl(page: number, search: string) {
		const parts: string[] = [];
		if (search) {
			parts.push(`q=${encodeURIComponent(search)}`);
		}
		if (page > 1) {
			parts.push(`page=${page}`);
		}
		const query = parts.join('&');
		return resolve(query ? `/tools/users?${query}` : '/tools/users');
	}

	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	function onSearchInput(value: string) {
		clearTimeout(searchTimer);
		// Debounce so a new request fires once the user pauses, not on every
		// keystroke. A search always resets to the first page. replaceState keeps
		// the history stack from filling with every intermediate query.
		searchTimer = setTimeout(() => {
			void goto(buildUrl(1, value.trim()), { replaceState: true, keepFocus: true });
		}, 300);
	}

	function goToPage(page: number) {
		void goto(buildUrl(page, data.search));
	}

	function userHref(id: string) {
		return resolve(`/tools/users/${id}`);
	}
</script>

<svelte:head>
	<title>Пользователи · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro
	description="Список всех пользователей. Найди по имени или почте и открой карточку."
/>

<div class="mx-auto w-full max-w-3xl space-y-4">
	<Search
		bind:value={searchValue}
		placeholder="Поиск по имени или почте"
		oninput={(event) => onSearchInput(event.currentTarget.value)}
	/>

	{#if data.users.length > 0}
		<div class="overflow-x-auto">
			<Table hoverable>
				<TableHead>
					<TableHeadCell>Имя</TableHeadCell>
					<TableHeadCell>Почта</TableHeadCell>
					<TableHeadCell>Билет</TableHeadCell>
					<TableHeadCell>Роль</TableHeadCell>
				</TableHead>
				<TableBody>
					{#each data.users as listedUser (listedUser.id)}
						<TableBodyRow>
							<TableBodyCell class="font-medium">
								<!-- The username is the link to the detail page: a real anchor
								     keeps the row reachable and openable by keyboard. -->
								<a
									href={userHref(listedUser.id)}
									class="text-primary-600 hover:underline dark:text-primary-400"
								>
									{listedUser.username}
								</a>
							</TableBodyCell>
							<TableBodyCell class="text-gray-500 dark:text-gray-400">
								{listedUser.email ?? '—'}
							</TableBodyCell>
							<TableBodyCell class="font-mono text-xs text-gray-500 dark:text-gray-400">
								{listedUser.ticket_number ?? '—'}
							</TableBodyCell>
							<TableBodyCell>
								<Badge color={getRoleColor(listedUser.role)}>
									{getRoleLabel(listedUser.role)}
								</Badge>
							</TableBodyCell>
						</TableBodyRow>
					{/each}
				</TableBody>
			</Table>
		</div>

		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<p class="text-xs text-gray-500 dark:text-gray-400">
				Показаны {rangeStart}–{rangeEnd} из {data.total}
			</p>
			<div class="flex items-center justify-center gap-2">
				<Button
					color="light"
					size="sm"
					disabled={data.page <= 1}
					onclick={() => goToPage(data.page - 1)}
				>
					<ArrowLeftOutline class="me-1 h-4 w-4" aria-hidden="true" />
					Назад
				</Button>
				<span class="text-xs text-gray-500 dark:text-gray-400">
					{data.page} / {totalPages}
				</span>
				<Button
					color="light"
					size="sm"
					disabled={data.page >= totalPages}
					onclick={() => goToPage(data.page + 1)}
				>
					Вперёд
					<ArrowRightOutline class="ms-1 h-4 w-4" aria-hidden="true" />
				</Button>
			</div>
		</div>
	{:else}
		<EmptyState
			icon={UsersGroupOutline}
			title="Никого не нашлось"
			message={data.search ? 'Попробуй изменить запрос.' : 'Пользователей пока нет.'}
		/>
	{/if}
</div>
