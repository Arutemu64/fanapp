<script lang="ts">
	import ScanLine from '@lucide/svelte/icons/scan-line';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import { getApiErrorCode, gotNoApiAnswer } from '#lib/api/errors.js';
	import {
		findQuestPlayersOptions,
		getQuestPlayerOptions
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import BarcodeScannerDialog from '#lib/components/BarcodeScannerDialog.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import Username from '#lib/components/Username.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { isReachable } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { parseQuestCode } from '#lib/utils/questCode.js';

	import type { AwardTarget } from '../awardTarget.js';

	interface Props {
		onPick: (player: AwardTarget) => void;
		focusOnMount: boolean;
	}

	let { onPick, focusOnMount }: Props = $props();

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const QUEST_FORMATS = ['QRCode'] as const;
	const SEARCH_DEBOUNCE_MS = 300;

	let scanButton = $state<HTMLButtonElement | null>(null);
	let scannerOpen = $state(false);
	let lookingUp = $state(false);
	let searchValue = $state('');
	let searchTerm = $state('');
	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	const searchQuery = createQuery(() => ({
		...findQuestPlayersOptions({ query: { search: searchTerm } }),
		enabled: searchTerm !== ''
	}));
	let players = $derived(searchQuery.data?.players ?? []);
	let showResults = $derived(searchTerm !== '' && searchQuery.isSuccess && players.length > 0);
	let searchStatus = $derived.by(() => {
		if (searchTerm === '' || searchQuery.isPending) {
			return '';
		}
		if (searchQuery.isError) {
			return m.quest_tool_search_failed();
		}
		if (players.length === 0) {
			return m.quest_tool_search_empty();
		}
		return m.quest_tool_search_found({ count: players.length });
	});

	onMount(() => {
		if (focusOnMount) {
			scanButton?.focus();
		}
	});

	function handleSearchInput() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => (searchTerm = searchValue.trim()), SEARCH_DEBOUNCE_MS);
	}

	function handleDetect(text: string) {
		void handleScanned(text);
	}

	async function handleScanned(text: string) {
		const userNumber = parseQuestCode(text);
		if (userNumber === null) {
			toastService.add(m.quest_tool_invalid_code(), 'error');
			return;
		}
		if (!isReachable()) {
			onPick({ number: userNumber, unverified: true });
			return;
		}
		lookingUp = true;
		try {
			const player = await queryClient.query({
				...getQuestPlayerOptions({ path: { number: userNumber } }),
				staleTime: 0,
				retry: false,
				networkMode: 'always'
			});
			onPick(player);
		} catch (error) {
			if (getApiErrorCode(error) === 'USER_NOT_FOUND') {
				toastService.add(m.quest_tool_player_not_found(), 'error');
			} else if (gotNoApiAnswer(error)) {
				onPick({ number: userNumber, unverified: true });
			} else {
				toastService.add(m.quest_tool_search_failed(), 'error');
			}
		} finally {
			lookingUp = false;
		}
	}
</script>

<div class="flex flex-col gap-4">
	<Button
		bind:ref={scanButton}
		type="button"
		size="lg"
		class="w-full"
		disabled={lookingUp}
		onclick={() => (scannerOpen = true)}
	>
		{#if lookingUp}
			<Spinner data-icon="inline-start" />
		{:else}
			<ScanLine data-icon="inline-start" />
		{/if}
		{m.quest_tool_scan()}
	</Button>

	<Field.Field>
		<Field.FieldLabel for="quest-player-search">{m.quest_tool_search_label()}</Field.FieldLabel>
		<Input
			id="quest-player-search"
			type="search"
			bind:value={searchValue}
			placeholder={m.quest_tool_search_placeholder()}
			autocomplete="off"
			autocapitalize="off"
			spellcheck={false}
			enterkeyhint="search"
			oninput={handleSearchInput}
		/>
	</Field.Field>

	{#if searchTerm !== '' && searchQuery.isPending}
		<div class="flex justify-center py-2"><Spinner /></div>
	{/if}

	<p
		role="status"
		class={[
			'text-sm',
			searchQuery.isError ? 'text-destructive' : 'text-muted-foreground',
			(searchStatus === '' || showResults) && 'sr-only'
		]}
	>
		{searchStatus}
	</p>

	{#if showResults}
		<ul class="flex flex-col divide-y divide-border rounded-xl border border-border">
			{#each players as player (player.id)}
				<li>
					<button
						type="button"
						class="flex min-h-12 w-full items-center gap-3 px-3 py-2 text-left outline-none first:rounded-t-xl last:rounded-b-xl hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-inset active:bg-muted"
						onclick={() => onPick(player)}
					>
						<UserAvatar seed={player.avatar_seed} class="size-8" />
						<Username username={player.username} class="min-w-0 flex-1 text-base" />
						<span class="shrink-0 text-sm text-muted-foreground tabular-nums">
							{m.quest_points({ count: player.points })}
						</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<BarcodeScannerDialog
	bind:open={scannerOpen}
	title={m.quest_tool_scan_title()}
	description={m.quest_tool_scan_description()}
	formats={QUEST_FORMATS}
	onDetect={handleDetect}
/>
