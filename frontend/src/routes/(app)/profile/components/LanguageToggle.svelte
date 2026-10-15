<script lang="ts">
	import type { Locale } from '#lib/paraglide/runtime.js';

	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, locales, setLocale } from '#lib/paraglide/runtime.js';

	const labels: Record<Locale, () => string> = {
		ru: () => m.language_ru(),
		en: () => m.language_en()
	};

	const current = getLocale();
</script>

<div
	class="flex w-full rounded-lg border border-border p-1"
	role="group"
	aria-label={m.language_aria_label()}
>
	{#each locales as locale (locale)}
		<button
			type="button"
			aria-pressed={current === locale}
			lang={locale}
			onclick={() => setLocale(locale)}
			class={[
				'flex h-11 min-w-0 flex-1 items-center justify-center rounded-md px-1 text-sm transition-colors',
				current === locale
					? 'bg-muted font-medium text-foreground'
					: 'text-muted-foreground hover:text-foreground'
			]}
		>
			<span class="truncate">{labels[locale]()}</span>
		</button>
	{/each}
</div>
