<script lang="ts">
	import { Button, Modal } from 'flowbite-svelte';
	import { ArrowDownToBracketOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
	}

	let { open = $bindable(false) }: Props = $props();
</script>

<Modal bind:open size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<ArrowDownToBracketOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Установи приложение</h3>
		</div>
	{/snippet}

	<p class="text-sm text-gray-500 dark:text-gray-400">
		Пуш-уведомления на iOS доступны только в установленном приложении. Найди карточку «Установить
		приложение» на этой странице и следуй инструкции.
	</p>
	{#snippet footer()}
		<Button color="alternative" class="w-full" onclick={() => (open = false)}>Понятно</Button>
	{/snippet}
</Modal>
