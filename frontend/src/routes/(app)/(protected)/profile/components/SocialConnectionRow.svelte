<script lang="ts">
	import type { Snippet } from 'svelte';

	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import { Badge, Button, Spinner } from 'flowbite-svelte';
	import { TrashBinOutline } from 'flowbite-svelte-icons';

	interface Props {
		/** Provider mark, rendered next to the label. */
		icon: Snippet;
		label: string;
		connected: boolean;
		/** Description shown when the provider is linked / not linked. */
		connectedDescription: string;
		notConnectedDescription: string;
		/** Backend link URL, opened when the user connects the provider. */
		connectHref: string;
		/** Confirm-strip question, e.g. «Отвязать Telegram?». */
		unlinkPrompt: string;
		/**
		 * Unlink is blocked without an email so the user never loses their last
		 * recovery path — the backend enforces it too; this just hides the affordance.
		 */
		hasEmail: boolean;
		/** Performs the actual unlink (API call + toast + refresh). */
		onUnlink: () => Promise<void>;
	}

	let {
		icon,
		label,
		connected,
		connectedDescription,
		notConnectedDescription,
		connectHref,
		unlinkPrompt,
		hasEmail,
		onUnlink
	}: Props = $props();

	// Connecting (a backend OAuth redirect) and unlinking (a DELETE) both need the
	// network — gate them offline. The linked/not-linked badge still renders.
	const offlineGate = offlineWriteGate();

	let isUnlinking = $state(false);
	// Gate the destructive unlink behind a deliberate second tap (inline, no modal).
	let isConfirming = $state(false);

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

<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
	<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				{@render icon()}
				<p class="font-medium text-gray-900 dark:text-white">{label}</p>
				<Badge color={connected ? 'green' : 'gray'} border>
					{connected ? 'Подключён' : 'Не подключён'}
				</Badge>
			</div>

			<p class="mt-1.5 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
				{connected ? connectedDescription : notConnectedDescription}
			</p>
		</div>

		<div class="flex w-full flex-col gap-2 sm:w-auto">
			{#if connected}
				{#if isConfirming}
					<p class="text-sm font-medium text-gray-900 sm:text-right dark:text-white">
						{unlinkPrompt}
					</p>
					<div class="flex gap-2">
						<Button
							color="red"
							size="sm"
							class="min-h-11 flex-1 sm:flex-initial"
							disabled={isUnlinking || !hasEmail || offlineGate.disabled}
							title={offlineGate.title}
							onclick={confirmUnlink}
						>
							{#if isUnlinking}
								<Spinner class="me-2 h-4 w-4 fill-white" />
								Отвязка…
							{:else}
								<TrashBinOutline class="me-2 h-4 w-4" />
								Отвязать
							{/if}
						</Button>
						<Button
							color="alternative"
							size="sm"
							class="min-h-11 flex-1 sm:flex-initial"
							disabled={isUnlinking}
							onclick={() => (isConfirming = false)}
						>
							Отмена
						</Button>
					</div>
				{:else}
					<Button
						color="red"
						size="sm"
						class="min-h-11 w-full sm:w-auto"
						disabled={!hasEmail || offlineGate.disabled}
						title={offlineGate.title}
						onclick={() => (isConfirming = true)}
					>
						<TrashBinOutline class="me-2 h-4 w-4" />
						Отвязать
					</Button>
				{/if}
			{:else}
				<!-- Offline: drop href so Flowbite renders a real <button> that honours
					`disabled` (an <a> ignores it), blocking the OAuth redirect. -->
				<Button
					href={offlineGate.disabled ? undefined : connectHref}
					color="alternative"
					class="min-h-11 w-full sm:w-auto"
					disabled={offlineGate.disabled}
					title={offlineGate.title}
				>
					Подключить
				</Button>
			{/if}
		</div>
	</div>
</div>
