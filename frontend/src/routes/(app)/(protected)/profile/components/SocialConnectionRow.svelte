<script lang="ts">
	import type { Snippet } from 'svelte';

	import { Button } from '$lib/components/ui/button';
	import * as Item from '$lib/components/ui/item';
	import { Spinner } from '$lib/components/ui/spinner';

	interface Props {
		/** Provider mark, rendered in the row's icon tile. */
		icon: Snippet;
		label: string;
		connected: boolean;
		/** Backend link URL, opened when the user connects the provider. */
		connectHref: string;
		/** Confirm-strip question, e.g. «Отвязать Telegram?». */
		unlinkPrompt: string;
		/**
		 * Unlink is blocked without an email so the user never loses their last
		 * recovery path — the backend enforces it too; this just disables the
		 * affordance and says why in the status line.
		 */
		hasEmail: boolean;
		/** Performs the actual unlink (API call + toast + refresh). */
		onUnlink: () => Promise<void>;
	}

	let { icon, label, connected, connectHref, unlinkPrompt, hasEmail, onUnlink }: Props = $props();

	let isUnlinking = $state(false);
	// Gate the destructive unlink behind a deliberate second tap (inline, no modal).
	let isConfirming = $state(false);

	// The status line says why "Отвязать" is disabled, next to the button, rather
	// than in a notice under the whole group (Android settings: explain why a
	// dependent setting is unavailable, where it is).
	let status = $derived.by(() => {
		if (!connected) {
			return 'Не подключён';
		}
		if (!hasEmail) {
			return 'Подключён. Чтобы отвязать, сначала добавь почту';
		}
		return 'Подключён';
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

<!-- No border/radius of its own: the parent SignInMethods groups this row with the
	others in a single bordered container and supplies the divider between them. -->
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
			<Button href={connectHref} variant="outline" size="sm" class="min-h-11">Подключить</Button>
		</Item.Actions>
	{:else if !isConfirming}
		<!-- Neutral at rest: the red is saved for the confirm step, where the
		     destructive choice is actually made. -->
		<Item.Actions>
			<Button
				variant="outline"
				size="sm"
				class="min-h-11"
				disabled={!hasEmail}
				onclick={() => (isConfirming = true)}
			>
				Отвязать
			</Button>
		</Item.Actions>
	{:else}
		<!-- basis-full wraps the confirm strip onto its own line under the row. -->
		<div class="flex basis-full flex-col gap-2">
			<p class="text-sm font-medium text-foreground">{unlinkPrompt}</p>
			<div class="flex gap-2">
				<Button
					variant="destructive"
					size="sm"
					class="min-h-11 flex-1"
					disabled={isUnlinking || !hasEmail}
					onclick={confirmUnlink}
				>
					{#if isUnlinking}
						<Spinner data-icon="inline-start" />
						Отвязка…
					{:else}
						Отвязать
					{/if}
				</Button>
				<Button
					variant="outline"
					size="sm"
					class="min-h-11 flex-1"
					disabled={isUnlinking}
					onclick={() => (isConfirming = false)}
				>
					Отмена
				</Button>
			</div>
		</div>
	{/if}
</Item.Root>
