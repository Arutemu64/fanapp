<script lang="ts">
	import type { Picture } from '@sveltejs/enhanced-img';

	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { CloseOutline, DownloadOutline } from 'flowbite-svelte-icons';

	interface MapEntry {
		id: string;
		picture: Picture;
		alt: string;
		// File name used when downloading the map.
		filename: string;
	}

	// Alt text is the only per-file metadata that can't be derived from the file:
	// it's human-authored Russian and required for accessibility. Intrinsic
	// dimensions, formats and responsive sizes come from <enhanced:img> at build
	// time, so dropping in a map of any proportions needs only its alt entry here.
	const ALT: Record<string, string> = {
		'map_1.jpg': 'Карта площадки 1',
		'map_2_3.jpg': 'Карта площадки 2 и 3'
	};

	// enhanced-img processes each match at build into a Picture (AVIF/WebP + sized
	// variants, content-hashed so a swap busts every cache layer — browser, CDN,
	// service worker). eager inlines the objects; import:'default' unwraps each
	// module to its Picture.
	const modules = import.meta.glob<Picture>('$lib/assets/map/*.jpg', {
		eager: true,
		query: { enhanced: true },
		import: 'default'
	});

	// Build the gallery from the discovered files, attaching alt text by name and
	// sorting by id so the order is stable regardless of glob iteration order.
	const maps: MapEntry[] = Object.entries(modules)
		.map(([path, picture]) => {
			const filename = path.split('/').pop() ?? '';
			const alt = ALT[filename];
			if (!alt) return null;
			return {
				id: filename.replace(/\.[^.]+$/, ''),
				picture,
				alt,
				filename
			};
		})
		.filter((entry): entry is MapEntry => entry !== null)
		.sort((a, b) => a.id.localeCompare(b.id));

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

<div class="space-y-4">
	{#each maps as map (map.id)}
		<button
			type="button"
			onclick={() => (active = map)}
			class="block w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-100 p-2 shadow-sm transition-colors hover:bg-gray-200/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 dark:border-gray-800 dark:bg-gray-950 dark:hover:bg-gray-800/80"
			aria-label={`Открыть карту на весь экран: ${map.alt}`}
		>
			<enhanced:img
				src={map.picture}
				alt={map.alt}
				loading="lazy"
				sizes="(min-width: 1024px) 1024px, 100vw"
				class="max-h-[70dvh] w-full rounded-xl object-contain"
			/>
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

		<!-- max-w caps the size on desktop so the image isn't stretched. relative keeps it above the backdrop. -->
		<enhanced:img
			src={active.picture}
			alt={active.alt}
			sizes="(min-width: 1024px) 1024px, 100vw"
			class="relative max-h-full w-full max-w-5xl rounded-xl object-contain shadow-2xl"
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
