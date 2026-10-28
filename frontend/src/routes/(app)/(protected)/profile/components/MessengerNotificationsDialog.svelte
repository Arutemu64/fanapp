<script lang="ts">
	import type { Snippet } from 'svelte';

	import MessageSquare from '@lucide/svelte/icons/message-square';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	interface Props {
		open: boolean;
		title: string;
		intro: string;
		/** `<li>` items, numbered by the dialog. */
		steps: Snippet;
		chatUrl?: string | null;
		chatLabel?: string;
		/** Without a linked account there is nothing to check yet. */
		canCheck: boolean;
		/** Asks the server to turn the channel on; it refuses until the messenger lets us write. */
		enable: () => Promise<unknown>;
		enabledMessage: string;
	}

	let {
		open = $bindable(false),
		title,
		intro,
		steps,
		chatUrl = null,
		chatLabel,
		canCheck,
		enable,
		enabledMessage
	}: Props = $props();

	const queryClient = useQueryClient();
	const toastService = getToastService();
	const offlineGate = offlineWriteGate();

	const enableMutation = createMutation(() => ({
		mutationFn: enable,
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
			toastService.add(enabledMessage, 'success');
			open = false;
		}
	}));

	let checkError = $derived(
		enableMutation.isError
			? (getApiErrorDetail(enableMutation.error) ?? m.toast_action_failed())
			: null
	);

	function onOpenChange(isOpen: boolean) {
		if (!isOpen) {
			enableMutation.reset();
		}
	}
</script>

<Dialog.Root bind:open {onOpenChange}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<MessageSquare class="size-5 text-muted-foreground" />
				{title}
			</Dialog.Title>
		</Dialog.Header>

		<Dialog.Description class="leading-relaxed">
			{intro}
		</Dialog.Description>
		<p class="text-sm font-medium text-foreground">{m.messenger_modal_steps_title()}</p>
		<ol class="flex list-decimal flex-col gap-1 ps-5 text-sm leading-relaxed text-muted-foreground">
			{@render steps()}
		</ol>
		{#if checkError}
			<p class="text-sm leading-relaxed text-destructive" role="alert">{checkError}</p>
		{/if}
		<Dialog.Footer class="flex flex-col gap-2 sm:flex-col">
			{#if chatUrl && chatLabel}
				<Button
					class="w-full"
					variant={canCheck ? 'outline' : 'default'}
					href={chatUrl}
					target="_blank"
					rel="noopener"
				>
					{chatLabel}
				</Button>
			{/if}
			{#if canCheck}
				<Button
					class="w-full"
					disabled={enableMutation.isPending}
					aria-disabled={offlineGate.blocked}
					onclick={offlineGate.guard(() => enableMutation.mutate())}
				>
					{#if enableMutation.isPending}
						<Spinner data-icon="inline-start" />
					{/if}
					{m.messenger_check()}
				</Button>
			{:else}
				<Button variant="outline" class="w-full" onclick={() => (open = false)}
					>{m.common_got_it()}</Button
				>
			{/if}
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
