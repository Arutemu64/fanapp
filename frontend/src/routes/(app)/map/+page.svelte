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

	// The maps are landscape (~1.54:1) and phones are portrait, so a fit-to-screen
	// view lands around 28% of the file's native resolution — too small to read the
	// numbered legend. Zoomed swaps the fit for full viewport height, which on a
	// phone is roughly 1:1 with the source, and the container pans.
	let zoomed = $state(false);

	// A native <dialog> opened with showModal() is what makes the viewer usable
	// from a keyboard: it moves focus inside, keeps it there, marks the page
	// behind it inert (so a screen reader can't wander into it), restores focus
	// to the map button on close, and handles Escape — none of which a
	// role="dialog" div does on its own.
	async function openViewer(map: MapEntry) {
		active = map;
		zoomed = false;
		// Let the content render first so showModal() has a control to focus.
		await tick();
		viewer?.showModal();
	}

	function closeViewer() {
		viewer?.close();
	}

	// Clicks that land on the dialog or the pan area — anywhere but the image
	// itself, which is its own zoom button — are outside the map, so they dismiss.
	function handleViewerClick(event: MouseEvent) {
		if (event.target === viewer || event.target === panArea) {
			closeViewer();
		}
	}

	let panArea = $state<HTMLDivElement | null>(null);
</script>

<svelte:head>
	<title>Карта площадки · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Нажми на карту, чтобы открыть её на весь экран, и ещё раз — чтобы приблизить."
/>

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
	class="relative m-0 h-dvh max-h-none w-full max-w-none border-0 bg-black/80 p-0 backdrop:bg-black/80"
>
	{#if active}
		<!-- Edge to edge: no padding, so a landscape map gets the whole width on a
			phone. `m-auto` on the image (rather than centring on this container) is
			what keeps the top-left reachable once the image overflows and this
			becomes the pan area — centred flex content clips its own overflow. -->
		<div bind:this={panArea} class="flex h-full w-full overflow-auto overscroll-contain">
			<!-- The image is its own zoom control, so the gesture is the obvious one
				(tap the map) and it still arrives as a labelled button in the tab order.
				The image is sized against the viewport rather than its parent: the button
				is `shrink-0` so it takes the image's own width, which would make a
				parent-relative `max-w-full` resolve to the natural size and never fit.
				The intrinsic width/height keep the frame from jumping while a cold-cached
				copy decodes. -->
			<button
				type="button"
				onclick={() => (zoomed = !zoomed)}
				aria-label={zoomed ? 'Отдалить карту' : 'Приблизить карту'}
				aria-pressed={zoomed}
				class={[
					'm-auto shrink-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white',
					zoomed ? 'cursor-zoom-out' : 'cursor-zoom-in'
				]}
			>
				<img
					src={active.src}
					alt={active.alt}
					width={active.width}
					height={active.height}
					class={[
						'shadow-2xl',
						zoomed ? 'h-[100dvh] max-w-none' : 'max-h-[100dvh] max-w-[100dvw] object-contain'
					]}
				/>
			</button>
		</div>

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
