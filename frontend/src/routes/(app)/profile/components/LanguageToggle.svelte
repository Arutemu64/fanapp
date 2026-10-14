<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, locales, setLocale } from '#lib/paraglide/runtime.js';

	// Each language is named in itself, so a reader who can't parse the current
	// UI language can still find theirs. Never translated.
	const NAMES = {
		ru: 'Русский',
		en: 'English'
	} as const;

	const current = getLocale();
</script>

<div
	class="flex w-full rounded-lg border border-border p-1"
	role="group"
	aria-label={m.language_label()}
>
	{#each locales as locale (locale)}
		<button
			type="button"
			lang={locale}
			aria-pressed={current === locale}
			onclick={() => setLocale(locale)}
			class={[
				'flex h-11 min-w-0 flex-1 items-center justify-center rounded-md px-1 text-sm transition-colors',
				current === locale
					? 'bg-muted font-medium text-foreground'
					: 'text-muted-foreground hover:text-foreground'
			]}
		>
			<span class="truncate">{NAMES[locale]}</span>
		</button>
	{/each}
</div>
