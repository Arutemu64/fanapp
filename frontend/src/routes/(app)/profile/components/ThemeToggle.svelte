<script lang="ts">
	import type { Component } from 'svelte';

	import { Monitor, Moon, Sun } from '@lucide/svelte';

	import { getThemeService, type ThemeMode } from '#lib/services/theme.svelte.js';

	const theme = getThemeService();

	const options: { mode: ThemeMode; label: string; Icon: Component }[] = [
		{ mode: 'system', label: 'Системная', Icon: Monitor },
		{ mode: 'light', label: 'Светлая', Icon: Sun },
		{ mode: 'dark', label: 'Тёмная', Icon: Moon }
	];
</script>

<div
	class="flex w-full rounded-lg border border-border p-1"
	role="group"
	aria-label="Тема оформления"
>
	{#each options as { mode, label, Icon } (mode)}
		<button
			type="button"
			aria-pressed={theme.mode === mode}
			onclick={() => theme.setMode(mode)}
			class={[
				'flex h-11 min-w-0 flex-1 items-center justify-center gap-1.5 rounded-md px-1 text-sm transition-colors',
				theme.mode === mode
					? 'bg-muted font-medium text-foreground'
					: 'text-muted-foreground hover:text-foreground'
			]}
		>
			<Icon class="size-4 shrink-0" aria-hidden="true" />
			<span class="truncate">{label}</span>
		</button>
	{/each}
</div>
