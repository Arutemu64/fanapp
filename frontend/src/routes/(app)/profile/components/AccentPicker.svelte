<script lang="ts">
	import { Check } from '@lucide/svelte';

	import { ACCENTS, getThemeService } from '#lib/services/theme.svelte.js';

	const theme = getThemeService();
</script>

<div class="flex w-full justify-between" role="group" aria-label="Цвет акцента">
	{#each ACCENTS as { id, label } (id)}
		<button
			type="button"
			aria-pressed={theme.accent === id}
			aria-label={label}
			title={label}
			onclick={() => theme.setAccent(id)}
			class="flex size-11 items-center justify-center rounded-full"
		>
			<!-- The swatch carries its own data-accent so it previews its preset
				whichever one is active; see app.css. -->
			<span
				data-accent={id}
				class={[
					'flex size-8 items-center justify-center rounded-full bg-primary-600 text-white',
					theme.accent === id && 'ring-2 ring-foreground ring-offset-2 ring-offset-background'
				]}
			>
				{#if theme.accent === id}
					<Check class="size-4" aria-hidden="true" />
				{/if}
			</span>
		</button>
	{/each}
</div>
