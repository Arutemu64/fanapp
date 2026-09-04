<script lang="ts">
	import * as Alert from '$lib/components/ui/alert';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { AlertCircle, BellRing } from '@lucide/svelte';

	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel: string;
		// Destructive actions (e.g. skipping) use the red button; everything else stays primary.
		confirmColor?: 'primary' | 'red';
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
		notifyTone = 'warning',
		onconfirm
	}: Props = $props();

	// Loud for new broadcasts (push can't be undone); quiet for reverting actions.
	let notifyMessage = $derived(
		notifyTone === 'warning'
			? 'Все подписчики получат уведомление. Пуш-уведомление нельзя будет отозвать.'
			: 'Подписчики получат уведомление об изменении.'
	);
</script>

<!-- AlertDialog (role="alertdialog"), not Dialog: these confirm an irreversible push
	broadcast, so the surface must not dismiss on an outside click and must force an
	explicit choice. AlertDialog.Action/Cancel close on their own via bind:open. -->
<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="flex items-center gap-2">
				<AlertCircle class="size-5 text-muted-foreground" />
				{title}
			</AlertDialog.Title>
			<AlertDialog.Description>{message}</AlertDialog.Description>
		</AlertDialog.Header>

		<!-- These actions fan out a mailing to every subscriber. Telegram messages can be undone, but delivered push notifications cannot, so warn before sending. -->
		{#if notifyTone === 'warning'}
			<Alert.Root variant="warning">
				<BellRing class="shrink-0" />
				<Alert.Description>{notifyMessage}</Alert.Description>
			</Alert.Root>
		{:else}
			<Alert.Root class="border-border bg-muted/50 text-muted-foreground">
				<BellRing class="size-4 shrink-0" />
				<Alert.Description>{notifyMessage}</Alert.Description>
			</Alert.Root>
		{/if}

		<AlertDialog.Footer>
			<AlertDialog.Cancel>Отмена</AlertDialog.Cancel>
			<AlertDialog.Action
				variant={confirmColor === 'red' ? 'destructive' : 'default'}
				onclick={onconfirm}
			>
				{confirmLabel}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
