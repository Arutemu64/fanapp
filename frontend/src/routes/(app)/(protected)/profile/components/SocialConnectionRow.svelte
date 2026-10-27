<script lang="ts">
	import type { Snippet } from 'svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Item from '#lib/components/ui/item/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	interface Props {
		icon: Snippet;
		label: string;
		connected: boolean;
		connectHref: string;
		unlinkPrompt: string;
		hasEmail: boolean;
		onUnlink: () => Promise<void>;
	}

	let { icon, label, connected, connectHref, unlinkPrompt, hasEmail, onUnlink }: Props = $props();

	const offlineGate = offlineWriteGate();

	let isUnlinking = $state(false);
	let isConfirming = $state(false);

	let status = $derived.by(() => {
		if (!connected) {
			return m.social_not_connected();
		}
		if (!hasEmail) {
			return m.social_connected_need_email();
		}
		return m.social_connected();
	});

	async function confirmUnlink() {
		if (isUnlinking) return;

		isUnlinking = true;
		try {
			await onUnlink();
		} finally {
			isUnlinking = false;
			isConfirming = false;
		}
	}
</script>

<Item.Root class="rounded-none">
	<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
		{@render icon()}
	</Item.Media>
	<Item.Content class="min-w-0">
		<Item.Title class="text-base">{label}</Item.Title>
		<Item.Description class="line-clamp-none">{status}</Item.Description>
	</Item.Content>

	{#if !connected}
		<Item.Actions>
			<Button
				href={connectHref}
				variant="outline"
				size="sm"
				class="min-h-11"
				aria-disabled={offlineGate.blocked}
				onclick={offlineGate.guard(() => {})}
			>
				{m.common_connect()}
			</Button>
		</Item.Actions>
	{:else if !isConfirming}
		<Item.Actions>
			<Button
				variant="outline"
				size="sm"
				class="min-h-11"
				disabled={!hasEmail}
				aria-disabled={offlineGate.blocked}
				onclick={offlineGate.guard(() => (isConfirming = true))}
			>
				{m.common_unlink()}
			</Button>
		</Item.Actions>
	{:else}
		<div class="flex basis-full flex-col gap-2">
			<p class="text-sm font-medium text-foreground">{unlinkPrompt}</p>
			<div class="flex gap-2">
				<Button
					variant="destructive"
					size="sm"
					class="min-h-11 flex-1"
					disabled={isUnlinking || !hasEmail}
					aria-disabled={offlineGate.blocked}
					onclick={offlineGate.guard(() => void confirmUnlink())}
				>
					{#if isUnlinking}
						<Spinner data-icon="inline-start" />
						{m.social_unlinking()}
					{:else}
						{m.common_unlink()}
					{/if}
				</Button>
				<Button
					variant="outline"
					size="sm"
					class="min-h-11 flex-1"
					disabled={isUnlinking}
					onclick={() => (isConfirming = false)}
				>
					{m.common_cancel()}
				</Button>
			</div>
		</div>
	{/if}
</Item.Root>
