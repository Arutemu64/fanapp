<script lang="ts">
	import { resolve } from '$app/paths';
	import { MessageSquare } from '@lucide/svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		open: boolean;
		/**
		 * Deep link to the community chat where the user grants «разрешить
		 * сообщения». Null when VK notifications were not configured for this
		 * deployment — the modal hides the button then.
		 */
		vkGroupUrl: string | null;
	}

	let { open = $bindable(false), vkGroupUrl }: Props = $props();
</script>

<Dialog.Root bind:open>
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
		<ul class="flex flex-col gap-1 text-sm leading-relaxed text-muted-foreground">
			<li>
				{m.vk_modal_step_connect_prefix()}
				<a href={resolve('profile/account')} class="font-medium text-primary hover:underline"
					>{m.vk_modal_step_connect_link()}</a
				>.
			</li>
			<li>{m.vk_modal_step_allow()}</li>
		</ul>
		<Dialog.Footer class="flex flex-col gap-2 sm:flex-col">
			{#if vkGroupUrl}
				<Button class="w-full" href={vkGroupUrl} target="_blank" rel="noopener">
					{m.vk_modal_open_community()}
				</Button>
			{/if}
			<Button variant="outline" class="w-full" onclick={() => (open = false)}
				>{m.common_got_it()}</Button
			>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
