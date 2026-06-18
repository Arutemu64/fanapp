<script lang="ts">
	import type { Component, Snippet } from 'svelte';

	interface Props {
		// 'warning' = stop-and-read (yellow); 'muted' = low-stakes FYI (gray).
		tone?: 'warning' | 'muted';
		// Optional leading icon, e.g. a flowbite-svelte-icons component.
		icon?: Component;
		// Plain message; ignored when a children snippet is provided.
		message?: string;
		// 'status' for passive notes, 'alert' for ones that interrupt a flow.
		role?: 'status' | 'alert';
		children?: Snippet;
	}

	// Rename the `icon` prop to a capitalized `Icon` so it can be rendered as a
	// component below (Svelte only treats capitalized names as components).
	let { tone = 'warning', icon: Icon, message, role = 'status', children }: Props = $props();
</script>

<div
	{role}
	class={[
		'flex items-start gap-2.5 rounded-xl border px-3 py-2.5 text-sm',
		tone === 'warning'
			? 'border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900/50 dark:bg-yellow-950/50 dark:text-yellow-200'
			: 'border-gray-200 bg-gray-50 text-gray-600 dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-300'
	]}
>
	{#if Icon}
		<Icon class="mt-px h-5 w-5 shrink-0" aria-hidden="true" />
	{/if}
	<p class="leading-snug">
		{#if children}{@render children()}{:else}{message}{/if}
	</p>
</div>
