<script lang="ts">
	import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import * as Alert from '$lib/components/ui/alert';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Button } from '$lib/components/ui/button';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Bell } from '@lucide/svelte';

	const client = createApiClient();

	interface Props {
		open: boolean;
		event: ScheduleEventWithSubscription;
	}
	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();
	let formError = $state('');

	$effect(() => {
		if (open) {
			formError = '';
		}
	});

	async function handleUnsubscribe() {
		if (!event.user_subscription) {
			open = false;
			return;
		}

		formError = '';
		const { error, response } = await client.DELETE('/schedule/subscriptions/{subscription_id}', {
			params: { path: { subscription_id: event.user_subscription.id } }
		});

		if (error || !response.ok) {
			console.error('Error unsubscribing:', error);
			formError = getApiErrorDetail(error) ?? 'Не удалось отключить уведомления';
			return;
		}

		toastService.add('Подписка на уведомления отключена', 'success');
		await invalidate('app:schedule');
		open = false;
	}
</script>

<!-- AlertDialog (role="alertdialog"), not Dialog: a confirmation that must force an
	explicit choice and not dismiss on an outside click. The confirm is a plain Button
	(not AlertDialog.Action) because the request is fired here and a failure must keep
	the dialog open to show formError — Action would auto-close and drop the message. -->
<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="flex items-center gap-2">
				<Bell class="size-5 text-muted-foreground" />
				Отписка от уведомлений
			</AlertDialog.Title>
			<AlertDialog.Description>
				Хочешь отписаться от уведомлений о выступлении <strong class="text-foreground"
					>{event.title}</strong
				>?
			</AlertDialog.Description>
		</AlertDialog.Header>

		{#if formError}
			<Alert.Root variant="destructive">
				<Alert.Description>{formError}</Alert.Description>
			</Alert.Root>
		{/if}

		<AlertDialog.Footer>
			<AlertDialog.Cancel>Отмена</AlertDialog.Cancel>
			<Button type="button" variant="destructive" onclick={handleUnsubscribe}>Отписаться</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
