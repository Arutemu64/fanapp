<script lang="ts">
	import type { Component } from 'svelte';

	import { getThemeService, type ThemeMode } from '$lib/services/theme.svelte';
	import { Monitor, Moon, Sun } from '@lucide/svelte';

	const theme = getThemeService();

	const options: { mode: ThemeMode; label: string; Icon: Component }[] = [
		{ mode: 'system', label: 'Системная', Icon: Monitor },
		{ mode: 'light', label: 'Светлая', Icon: Sun },
		{ mode: 'dark', label: 'Тёмная', Icon: Moon }
	];
</script>

<div class="flex rounded-lg border border-border p-1" role="group" aria-label="Тема оформления">
	{#each options as { mode, label, Icon } (mode)}
		<button
			type="button"
			aria-label={label}
			aria-pressed={theme.mode === mode}
			onclick={() => theme.setMode(mode)}
			class={[
				'flex flex-1 items-center justify-center rounded-md p-1.5 transition-colors',
				theme.mode === mode
					? 'bg-muted font-medium text-foreground'
					: 'text-muted-foreground hover:text-foreground'
			]}
		>
			<Icon class="size-4" />
		</button>
	{/each}
</div>
