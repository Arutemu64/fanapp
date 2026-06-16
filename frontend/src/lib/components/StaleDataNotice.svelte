<script lang="ts">
	import { ClockOutline } from 'flowbite-svelte-icons';

	// Shown when a page is rendering a cached copy because the network was down.
	let {
		message = 'Нет связи. Показаны сохранённые данные — обновятся при подключении.'
	}: {
		message?: string;
	} = $props();
</script>

<div
	role="status"
	class="flex items-center gap-2.5 rounded-xl border border-yellow-200 bg-yellow-50 px-3 py-2.5 text-sm text-yellow-800 dark:border-yellow-900/50 dark:bg-yellow-950/50 dark:text-yellow-200"
>
	<ClockOutline class="h-5 w-5 shrink-0" aria-hidden="true" />
	<p class="leading-snug">{message}</p>
</div>
