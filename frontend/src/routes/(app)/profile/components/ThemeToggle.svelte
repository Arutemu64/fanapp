<script lang="ts">
	import type { Component } from 'svelte';

	import { Monitor, Moon, Sun } from '@lucide/svelte';

	import { m } from '#lib/paraglide/messages.js';
	import { getThemeService, type ThemeMode } from '#lib/services/theme.svelte.js';

	const theme = getThemeService();

	const options: { mode: ThemeMode; label: string; Icon: Component }[] = [
		{ mode: 'system', label: m.theme_auto(), Icon: Monitor },
		{ mode: 'light', label: m.theme_light(), Icon: Sun },
		{ mode: 'dark', label: m.theme_dark(), Icon: Moon }
	];
</script>

<!-- A tonal track, not a bordered box: it sits inside a MenuGroup card, and DESIGN.md
     keeps boxes out of boxes. The picked segment lifts onto the card surface. -->
<div class="flex w-full rounded-lg bg-muted p-1" role="group" aria-label={m.theme_aria_label()}>
	{#each options as { mode, label, Icon } (mode)}
		<button
			type="button"
			aria-pressed={theme.mode === mode}
			onclick={() => theme.setMode(mode)}
			class={[
				'flex h-11 min-w-0 flex-1 items-center justify-center gap-1.5 rounded-md px-1 text-sm transition-colors',
				theme.mode === mode
					? 'bg-card font-medium text-foreground shadow-xs'
					: 'text-muted-foreground hover:text-foreground'
			]}
		>
			<Icon class="size-4 shrink-0" aria-hidden="true" />
			<span class="truncate">{label}</span>
		</button>
	{/each}
</div>
