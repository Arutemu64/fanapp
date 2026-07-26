<script lang="ts">
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { ExpandOutline } from 'flowbite-svelte-icons';

	import type { MapEntry } from './maps';

	import MapViewer from './components/MapViewer.svelte';
	import { maps } from './maps';

	// Currently opened map for the fullscreen viewer, or null when closed.
	let active = $state<MapEntry | null>(null);
</script>

<svelte:head>
	<title>Карта площадки · ФАН ФАН</title>
</svelte:head>

<SectionIntro description="Нажми на карту, чтобы открыть её на весь экран и приблизить." />

<div class="space-y-4">
	{#each maps as map (map.id)}
		<button
			type="button"
			onclick={() => (active = map)}
			class="block w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-100 p-2 shadow-sm transition-colors hover:bg-gray-200/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 dark:border-gray-800 dark:bg-gray-950 dark:hover:bg-gray-800/80"
			aria-label={`Открыть карту на весь экран: ${map.label}`}
		>
			<!-- w-auto rather than object-contain: the element then hugs the fitted
				image instead of letterboxing it inside a full-width box. -->
			<img
				src={map.src}
				alt={map.alt}
				width={map.width}
				height={map.height}
				loading="lazy"
				class="mx-auto h-auto max-h-[70dvh] w-auto max-w-full rounded-xl"
			/>

			<span class="flex items-center gap-2 px-1 pt-2 text-sm font-medium">
				<span class="flex-1 truncate text-start text-gray-900 dark:text-white">{map.label}</span>
				<ExpandOutline class="h-4 w-4 shrink-0 text-gray-500 dark:text-gray-400" />
			</span>
		</button>
	{:else}
		<div
			class="rounded-2xl border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400"
		>
			Карты пока не добавлены.
		</div>
	{/each}
</div>

{#if active}
	<MapViewer bind:entry={active} {maps} onclose={() => (active = null)} />
{/if}
