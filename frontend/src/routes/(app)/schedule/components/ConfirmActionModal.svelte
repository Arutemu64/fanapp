<script lang="ts">
	import BellRing from '@lucide/svelte/icons/bell-ring';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';

	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel: string;
		confirmColor?: 'primary' | 'red';
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

	let notifyMessage = $derived(
		notifyTone === 'warning' ? m.confirm_notify_push_warning() : m.confirm_notify_subscribers()
	);
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="flex items-center gap-2">
				<CircleAlert class="size-5 text-muted-foreground" />
				{title}
			</AlertDialog.Title>
			<AlertDialog.Description>{message}</AlertDialog.Description>
		</AlertDialog.Header>

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
			<AlertDialog.Cancel>{m.common_cancel()}</AlertDialog.Cancel>
			<AlertDialog.Action
				variant={confirmColor === 'red' ? 'destructive' : 'default'}
				onclick={onconfirm}
			>
				{confirmLabel}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
