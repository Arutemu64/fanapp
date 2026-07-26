<script lang="ts">
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { CloseOutline, DownloadOutline } from 'flowbite-svelte-icons';
	import { tick } from 'svelte';

	interface MapEntry {
		id: string;
		src: string;
		alt: string;
		width: number;
		height: number;
		// File name used when downloading the map.
		filename: string;
	}

	// Per-file metadata keyed by the source file name. Image URLs are discovered
	// from the bundle below, so adding a map needs only a new file in
	// $lib/assets/map plus an entry here (alt text + intrinsic dimensions, which
	// keep the layout stable while the image loads).
	const META: Record<string, { alt: string; width: number; height: number }> = {
		'map_1.jpg': { alt: 'Карта площадки 1', width: 1280, height: 831 },
		'map_2_3.jpg': { alt: 'Карта площадки 2 и 3', width: 1280, height: 787 }
	};

	// Vite resolves these imports to content-hashed URLs at build time, so a
	// swapped map busts every cache layer (browser, CDN, service worker)
	// automatically. eager = inline the URL strings; ?url = the asset URL rather
	// than the decoded module.
	const modules = import.meta.glob('$lib/assets/map/*.jpg', {
		eager: true,
		query: '?url',
		import: 'default'
	});

	// Build the gallery from the discovered files, attaching metadata by name and
	// sorting by id so the order is stable regardless of glob iteration order.
	const maps: MapEntry[] = Object.entries(modules)
		.map(([path, src]) => {
			const filename = path.split('/').pop() ?? '';
			const meta = META[filename];
			if (!meta) return null;
			return {
				id: filename.replace(/\.[^.]+$/, ''),
				src,
				alt: meta.alt,
				width: meta.width,
				height: meta.height,
				filename
			};
		})
		.filter((entry): entry is MapEntry => entry !== null)
		.sort((a, b) => a.id.localeCompare(b.id));

	// Currently opened map for the fullscreen viewer, or null when closed.
	let active = $state<MapEntry | null>(null);
	let viewer = $state<HTMLDialogElement | null>(null);

	// A native <dialog> opened with showModal() is what makes the viewer usable
	// from a keyboard: it moves focus inside, keeps it there, marks the page
	// behind it inert (so a screen reader can't wander into it), restores focus
	// to the map button on close, and handles Escape — none of which a
	// role="dialog" div does on its own.
	async function openViewer(map: MapEntry) {
		active = map;
		// Let the content render first so showModal() has a control to focus.
		await tick();
		viewer?.showModal();
	}

	function closeViewer() {
		viewer?.close();
	}

	// Clicks that land on the dialog element itself — its padding or the
	// ::backdrop — are outside the image, so they dismiss the viewer.
	function handleViewerClick(event: MouseEvent) {
		if (event.target === viewer) {
			closeViewer();
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
			onclick={() => void openViewer(map)}
			class="block w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-100 p-2 shadow-sm transition-colors hover:bg-gray-200/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 dark:border-gray-800 dark:bg-gray-950 dark:hover:bg-gray-800/80"
			aria-label={`Открыть карту на весь экран: ${map.alt}`}
		>
			<img
				src={map.src}
				alt={map.alt}
				width={map.width}
				height={map.height}
				loading="lazy"
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

<!-- Fullscreen viewer. Tap outside the image, press Escape, or use the close
	button to dismiss. `onclose` fires for all three, so it owns clearing `active`.
	The dim lives on the dialog, which fills the viewport, rather than on
	::backdrop alone — same look, minus the top-layer compositing differences
	between browsers. The ::backdrop rule still covers the letterboxing that
	appears when the visual viewport and dvh disagree (mobile URL bar). -->
<dialog
	bind:this={viewer}
	onclose={() => (active = null)}
	onclick={handleViewerClick}
	aria-label="Просмотр карты"
	class="relative m-0 flex h-dvh max-h-none w-full max-w-none items-center justify-center border-0 bg-black/80 p-4 backdrop:bg-black/80"
>
	{#if active}
		<!-- max-w caps the size on desktop so the image isn't stretched. The intrinsic
			size keeps the frame from jumping while a cold-cached copy decodes. -->
		<img
			src={active.src}
			alt={active.alt}
			width={active.width}
			height={active.height}
			class="max-h-full w-full max-w-5xl rounded-xl object-contain shadow-2xl"
		/>

		<div class="absolute end-4 top-4 flex items-center gap-2">
			<a
				href={active.src}
				download={active.filename}
				rel="external"
				class="flex h-11 w-11 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Скачать карту"
			>
				<DownloadOutline class="h-6 w-6" aria-hidden="true" />
			</a>
			<button
				type="button"
				onclick={closeViewer}
				class="flex h-11 w-11 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Закрыть"
			>
				<CloseOutline class="h-6 w-6" aria-hidden="true" />
			</button>
		</div>
	{/if}
</dialog>
