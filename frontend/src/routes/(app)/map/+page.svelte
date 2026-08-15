<script lang="ts">
	import type { MapEntry } from '$lib/data/maps';

	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { maps } from '$lib/data/maps';
	import { CloseOutline, DownloadOutline } from 'flowbite-svelte-icons';

	// Currently opened map for the fullscreen viewer, or null when closed.
	let active = $state<MapEntry | null>(null);

	function close() {
		active = null;
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}
</script>

<svelte:head>
	<title>Карта площадки · ФАН ФАН</title>
</svelte:head>

<SectionIntro description="Нажми на карту, чтобы открыть её на весь экран." />

<!-- Stacked on mobile, side by side from lg so the now-portrait maps sit next to
each other on desktop. items-start keeps each frame at its own height. -->
<div class="grid items-start gap-4 lg:grid-cols-2">
	{#each maps as map (map.id)}
		<!-- w-fit makes the frame hug the image so a portrait map is centred without
		side letterboxing; the image sizes to its intrinsic ratio, capped to the
		container width and 70dvh so a tall map never overflows the viewport. -->
		<button
			type="button"
			onclick={() => (active = map)}
			class="mx-auto block w-fit max-w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-100 p-2 shadow-sm transition-colors hover:bg-gray-200/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 dark:border-gray-800 dark:bg-gray-950 dark:hover:bg-gray-800/80"
			aria-label={`Открыть карту на весь экран: ${map.alt}`}
		>
			<enhanced:img
				src={map.picture}
				alt={map.alt}
				loading="lazy"
				sizes="(min-width: 1024px) 1024px, 100vw"
				class="block max-h-[70dvh] w-auto max-w-full rounded-xl"
			/>
		</button>
	{:else}
		<div
			class="rounded-2xl border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500 lg:col-span-2 dark:border-gray-700 dark:text-gray-400"
		>
			Карты пока не добавлены.
		</div>
	{/each}
</div>

{#if active}
	<!-- Fullscreen viewer overlay. Tap the backdrop or the close button to dismiss. -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
		role="dialog"
		aria-modal="true"
		aria-label="Просмотр карты"
	>
		<!-- Full-size backdrop button sits behind the image so a tap outside it closes the viewer. -->
		<button
			type="button"
			onclick={close}
			class="absolute inset-0 cursor-default"
			aria-label="Закрыть просмотр"
		></button>

		<!-- Caps are viewport units, not max-h-full: enhanced:img wraps the <img> in
		an inline <picture> with no definite height, so a percentage max-height never
		resolves and a tall portrait map overflows the viewport. 2rem matches the
		overlay's p-4. w-auto sizes to the intrinsic ratio and never upscales.
		relative keeps it above the backdrop, and hugging means the black area beside
		a portrait map is the backdrop button, so a tap there still closes the viewer. -->
		<enhanced:img
			src={active.picture}
			alt={active.alt}
			sizes="(min-width: 1024px) 1024px, 100vw"
			class="relative block max-h-[calc(100dvh-2rem)] w-auto max-w-[calc(100vw-2rem)] rounded-xl shadow-2xl"
		/>

		<div class="absolute end-4 top-4 z-10 flex items-center gap-2">
			<!-- Download the full-size fallback (img.src is the largest, original-format variant). -->
			<a
				href={active.picture.img.src}
				download={active.filename}
				rel="external"
				class="flex h-11 w-11 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Скачать карту"
			>
				<DownloadOutline class="h-6 w-6" />
			</a>
			<button
				type="button"
				onclick={close}
				class="flex h-11 w-11 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Закрыть"
			>
				<CloseOutline class="h-6 w-6" />
			</button>
		</div>
	</div>
{/if}

<svelte:window onkeydown={onKeydown} />
