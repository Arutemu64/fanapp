<script lang="ts">
	import { Button, Card } from 'flowbite-svelte';
	import { CloseCircleOutline } from 'flowbite-svelte-icons';

	let { data } = $props();
</script>

<div class="flex h-full items-center justify-center p-4">
	<Card class="w-full max-w-md p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			<CloseCircleOutline class="mx-auto mb-4 h-16 w-16 text-red-500" />
			<h2 class="mb-2 text-xl font-bold text-gray-900 dark:text-white">
				Не удалось выполнить вход
			</h2>
			<p class="mb-6 text-gray-500 dark:text-gray-400">
				{data.errorMessage}
			</p>
			<Button
				href="/login"
				outline
				color="dark"
				class="min-h-11 w-full rounded-xl transition-all hover:-translate-y-0.5 hover:shadow-md"
			>
				Вернуться ко входу
			</Button>
		</div>
	</Card>
</div>
