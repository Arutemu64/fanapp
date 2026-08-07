<script lang="ts">
	import { Button, Modal } from 'flowbite-svelte';
	import { AnnotationOutline } from 'flowbite-svelte-icons';

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

<Modal bind:open size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<AnnotationOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Уведомления во ВКонтакте</h3>
		</div>
	{/snippet}

	<p class="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
		Чтобы получать уведомления во ВКонтакте, нужно разрешить сообществу писать тебе — без этого
		ВКонтакте не доставит сообщения.
	</p>
	<p class="mt-3 text-sm font-medium text-gray-900 dark:text-gray-300">Что сделать:</p>
	<ul
		class="mt-1 list-disc space-y-1 ps-5 text-sm leading-relaxed text-gray-500 dark:text-gray-400"
	>
		<li>Подключи аккаунт ВКонтакте в блоке «Способы входа».</li>
		<li>Открой сообщество и нажми «Разрешить сообщения».</li>
	</ul>
	{#snippet footer()}
		{#if vkGroupUrl}
			<Button color="primary" class="w-full" href={vkGroupUrl} target="_blank" rel="noopener">
				Открыть сообщество
			</Button>
		{/if}
		<Button color="alternative" class="w-full" onclick={() => (open = false)}>Понятно</Button>
	{/snippet}
</Modal>
