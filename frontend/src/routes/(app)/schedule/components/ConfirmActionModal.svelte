<script lang="ts">
	import { Button, Modal } from 'flowbite-svelte';
	import { ExclamationCircleOutline, BellActiveOutline } from 'flowbite-svelte-icons';
	import NoticeCallout from '$lib/components/NoticeCallout.svelte';

	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel: string;
		// Destructive actions (e.g. skipping) use the red button; everything else stays primary.
		confirmColor?: 'primary' | 'red';
		// Whether to show the notification note. Schedule management actions
		// broadcast to every subscriber, so it is on by default.
		notify?: boolean;
		// 'warning' for actions that push new info (a loud yellow note about the
		// un-recallable push); 'muted' for reverting actions, where the broadcast
		// is just an update and a quiet FYI is enough.
		notifyTone?: 'warning' | 'muted';
		onconfirm: () => void;
	}

	let {
		open = $bindable(),
		title,
		message,
		confirmLabel,
		confirmColor = 'primary',
		notify = true,
		notifyTone = 'warning',
		onconfirm
	}: Props = $props();

	// Loud for new broadcasts (push can't be undone); quiet for reverting actions.
	let notifyMessage = $derived(
		notifyTone === 'warning'
			? 'Все подписчики получат уведомление. Push-уведомление нельзя будет отозвать.'
			: 'Подписчики получат уведомление об изменении.'
	);

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
			<NoticeCallout
				tone={notifyTone}
				icon={BellActiveOutline}
				message={notifyMessage}
				role="alert"
			/>
		{/if}
	</div>

	{#snippet footer()}
		<Button type="button" color="alternative" onclick={() => (open = false)}>Отмена</Button>
		<Button type="button" color={confirmColor} onclick={handleConfirm}>{confirmLabel}</Button>
	{/snippet}
</Modal>
