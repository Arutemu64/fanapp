<script lang="ts">
	import { resolve } from '$app/paths';
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import MessageSquare from '@lucide/svelte/icons/message-square';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { MessageTagProps } from '#lib/types/markup.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		enableVkNotificationsMutation,
		getCurrentUserQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	interface Props {
		open: boolean;
		vkGroupUrl: string | null;
		hasVkAccount: boolean;
	}

	let { open = $bindable(false), vkGroupUrl, hasVkAccount }: Props = $props();

	const queryClient = useQueryClient();
	const toastService = getToastService();
	const offlineGate = offlineWriteGate();

	const enableMutation = createMutation(() => ({
		...enableVkNotificationsMutation(),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
			toastService.add(m.vk_enabled(), 'success');
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
				{m.vk_modal_title()}
			</Dialog.Title>
		</Dialog.Header>

		<Dialog.Description class="leading-relaxed">
			{m.vk_modal_intro()}
		</Dialog.Description>
		<p class="text-sm font-medium text-foreground">{m.vk_modal_steps_title()}</p>
		<ol class="flex list-decimal flex-col gap-1 ps-5 text-sm leading-relaxed text-muted-foreground">
			{#if !hasVkAccount}
				<li>
					<ParaglideMessage message={m.vk_modal_step_connect}>
						{#snippet link({ children }: MessageTagProps)}
							<a href={resolve('profile/account')} class="font-medium text-primary hover:underline"
								>{@render children?.()}</a
							>
						{/snippet}
					</ParaglideMessage>
				</li>
			{/if}
			<li>{m.vk_modal_step_allow()}</li>
			{#if hasVkAccount}
				<li>{m.vk_modal_step_check()}</li>
			{/if}
		</ol>
		{#if checkError}
			<p class="text-sm leading-relaxed text-destructive" role="alert">{checkError}</p>
		{/if}
		<Dialog.Footer class="flex flex-col gap-2 sm:flex-col">
			{#if vkGroupUrl}
				<Button
					class="w-full"
					variant={hasVkAccount ? 'outline' : 'default'}
					href={vkGroupUrl}
					target="_blank"
					rel="noopener"
				>
					{m.vk_modal_open_community()}
				</Button>
			{/if}
			{#if hasVkAccount}
				<Button
					class="w-full"
					disabled={enableMutation.isPending}
					aria-disabled={offlineGate.blocked}
					onclick={offlineGate.guard(() => enableMutation.mutate({}))}
				>
					{#if enableMutation.isPending}
						<Spinner data-icon="inline-start" />
					{/if}
					{m.vk_check()}
				</Button>
			{:else}
				<Button variant="outline" class="w-full" onclick={() => (open = false)}
					>{m.common_got_it()}</Button
				>
			{/if}
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
