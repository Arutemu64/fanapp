<script lang="ts">
	import { ScanLine } from '@lucide/svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';

	import type { QuestPlayerDto } from '#lib/api/generated/index.js';

	import { getApiErrorCode } from '#lib/api/errors.js';
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
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { parseQuestCode } from '#lib/utils/questCode.js';

	interface Props {
		onPick: (player: QuestPlayerDto) => void;
	}

	let { onPick }: Props = $props();

	const toastService = getToastService();
	const queryClient = useQueryClient();

	// Player codes are always QR; scanning nothing else keeps a ticket barcode
	// on the same badge from being read first.
	const QUEST_FORMATS = ['QRCode'] as const;
	const SEARCH_DEBOUNCE_MS = 300;

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

	function handleSearchInput() {
		clearTimeout(searchTimer);
		// Debounce so a request fires once the volunteer pauses, not per keystroke.
		searchTimer = setTimeout(() => (searchTerm = searchValue.trim()), SEARCH_DEBOUNCE_MS);
	}

	function handleDetect(text: string) {
		void handleScanned(text);
	}

	async function handleScanned(text: string) {
		const userId = parseQuestCode(text);
		if (userId === null) {
			toastService.add(m.quest_tool_invalid_code(), 'error');
			return;
		}
		lookingUp = true;
		try {
			// Fresh, not cached: the form shows the player's current balance.
			const player = await queryClient.query({
				...getQuestPlayerOptions({ path: { user_id: userId } }),
				staleTime: 0
			});
			onPick(player);
		} catch (error) {
			if (getApiErrorCode(error) === 'USER_NOT_FOUND') {
				toastService.add(m.quest_tool_player_not_found(), 'error');
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

	{#if searchTerm !== ''}
		{#if searchQuery.isPending}
			<div class="flex justify-center py-2"><Spinner /></div>
		{:else if searchQuery.isError}
			<p class="text-sm text-destructive">{m.quest_tool_search_failed()}</p>
		{:else if players.length === 0}
			<p class="text-sm text-muted-foreground">{m.quest_tool_search_empty()}</p>
		{:else}
			<ul class="flex flex-col divide-y divide-border rounded-xl border border-border">
				{#each players as player (player.id)}
					<li>
						<button
							type="button"
							class="flex min-h-12 w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted"
							onclick={() => onPick(player)}
						>
							<UserAvatar seed={player.avatar_seed} class="size-8" />
							<span class="min-w-0 flex-1 truncate text-base">@{player.username}</span>
							<span class="shrink-0 text-sm text-muted-foreground tabular-nums">
								{m.quest_points({ count: player.points })}
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</div>

<BarcodeScannerDialog
	bind:open={scannerOpen}
	title={m.quest_tool_scan_title()}
	description={m.quest_tool_scan_description()}
	formats={QUEST_FORMATS}
	onDetect={handleDetect}
/>
