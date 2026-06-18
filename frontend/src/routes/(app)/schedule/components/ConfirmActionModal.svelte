<script lang="ts">
	import { Button, Modal } from 'flowbite-svelte';
	import { ExclamationCircleOutline, BellActiveOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel: string;
		// Destructive actions (e.g. skipping) use the red button; everything else stays primary.
		confirmColor?: 'primary' | 'red';
		// Whether to show the "subscribers will be notified" warning. Schedule
		// management actions broadcast a push that cannot be recalled, so it is on
		// by default.
		notify?: boolean;
		onconfirm: () => void;
	}

	let {
		open = $bindable(),
		title,
		message,
		confirmLabel,
		confirmColor = 'primary',
		notify = true,
		onconfirm
	}: Props = $props();

	function handleConfirm() {
		// Close first so a slow request never leaves the dialog hanging open.
		open = false;
		onconfirm();
	}
</script>

<Modal bind:open size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<ExclamationCircleOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">{title}</h3>
		</div>
	{/snippet}

	<div class="flex flex-col gap-3">
		<p class="text-sm text-gray-600 sm:text-base dark:text-gray-400">{message}</p>

		{#if notify}
			<!-- These actions fan out a mailing to every subscriber. Telegram messages can be undone, but delivered push notifications cannot, so warn before sending. -->
			<div
				class="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
			>
				<BellActiveOutline class="mt-0.5 h-4 w-4 shrink-0" />
				<span>Все подписчики получат уведомление. Push-уведомление нельзя будет отозвать.</span>
			</div>
		{/if}
	</div>

	{#snippet footer()}
		<Button type="button" color="alternative" onclick={() => (open = false)}>Отмена</Button>
		<Button type="button" color={confirmColor} onclick={handleConfirm}>{confirmLabel}</Button>
	{/snippet}
</Modal>
