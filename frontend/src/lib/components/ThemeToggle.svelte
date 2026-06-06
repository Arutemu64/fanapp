<script lang="ts">
	import { getThemeService, type ThemeMode } from '$lib/services/theme.svelte';
	import { DesktopPcOutline, MoonOutline, SunOutline } from 'flowbite-svelte-icons';
	import type { Component } from 'svelte';

	const theme = getThemeService();

	const options: { mode: ThemeMode; label: string; Icon: Component }[] = [
		{ mode: 'system', label: 'Системная', Icon: DesktopPcOutline },
		{ mode: 'light', label: 'Светлая', Icon: SunOutline },
		{ mode: 'dark', label: 'Тёмная', Icon: MoonOutline }
	];
</script>

<div
	class="flex rounded-lg border border-gray-200 p-1 dark:border-gray-700"
	role="group"
	aria-label="Тема оформления"
>
	{#each options as { mode, label, Icon } (mode)}
		<button
			type="button"
			aria-label={label}
			aria-pressed={theme.mode === mode}
			onclick={() => theme.setMode(mode)}
			class={[
				'flex flex-1 items-center justify-center rounded-md p-1.5 transition-colors',
				theme.mode === mode
					? 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white'
					: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
			]}
		>
			<Icon class="h-4 w-4" />
		</button>
	{/each}
</div>
