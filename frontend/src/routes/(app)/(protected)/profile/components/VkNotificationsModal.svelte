<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import { MessageSquare } from '@lucide/svelte';

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
				Уведомления во ВКонтакте
			</Dialog.Title>
		</Dialog.Header>

		<Dialog.Description class="leading-relaxed">
			Чтобы получать уведомления во ВКонтакте, нужно разрешить сообществу писать тебе — без этого
			ВКонтакте не доставит сообщения.
		</Dialog.Description>
		<p class="text-sm font-medium text-foreground">Что сделать:</p>
		<ul class="flex flex-col gap-1 text-sm leading-relaxed text-muted-foreground">
			<li>Подключи аккаунт ВКонтакте в блоке «Способы входа».</li>
			<li>Открой сообщество и нажми «Разрешить сообщения».</li>
		</ul>
		<Dialog.Footer class="flex flex-col gap-2 sm:flex-col">
			{#if vkGroupUrl}
				<Button class="w-full" href={vkGroupUrl} target="_blank" rel="noopener">
					Открыть сообщество
				</Button>
			{/if}
			<Button variant="outline" class="w-full" onclick={() => (open = false)}>Понятно</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
