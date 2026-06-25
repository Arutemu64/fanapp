<script lang="ts">
	interface Props {
		// When set, renders a bold heading above the message (two-line variant).
		title?: string;
		message: string;
	}

	let { title, message }: Props = $props();
</script>

<div
	class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800"
>
	{#if title}
		<p class="text-base font-bold text-gray-900 dark:text-white">{title}</p>
		<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{message}</p>
	{:else}
		<p class="text-gray-500 dark:text-gray-400">{message}</p>
	{/if}
</div>
