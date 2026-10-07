<script lang="ts">
	import type { MapEntry } from '$lib/data/maps';
	import type { SlideData, UIElementData } from 'photoswipe';

	import { pushState } from '$app/navigation';
	import { page } from '$app/state';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { maps } from '$lib/data/maps';
	import PhotoSwipe from 'photoswipe';
	import 'photoswipe/style.css';

	// Thumbnail buttons, indexed like `maps`. PhotoSwipe animates the open and
	// close from each one's <img>, and returns focus to the one that opened it.
	const thumbnails: HTMLButtonElement[] = [];

	// The open viewer. Not $state: nothing renders from it.
	let viewer: PhotoSwipe | null = null;

	// The viewer lives on its own history entry (shallow routing), so the phone's
	// back gesture closes the map instead of leaving the page — the case
	// https://svelte.dev/docs/kit/shallow-routing is written for. A thumbnail only
	// pushes the entry; the effect below opens and closes the viewer from it, so
	// back, forward and the viewer's own close controls all go through one path.
	function openMap(index: number) {
		pushState('', { mapViewerIndex: index });
	}

	$effect(() => {
		const index = page.state.mapViewerIndex;
		if (index === undefined || !maps[index]) {
			closeViewer();
			return;
		}
		if (!viewer) {
			viewer = createViewer(index);
		}
	});

	// Closes the viewer the page state no longer asks for (back gesture, or leaving
	// the page). Letting go of `viewer` first tells the close handler below that
	// the history entry is already gone. PhotoSwipe ignores close() — and destroy(),
	// which goes through it — until its opening animation ends, so a back gesture
	// made that quickly would strand the viewer open without the deferral.
	function closeViewer() {
		const closing = viewer;
		if (!closing) return;
		viewer = null;
		if (closing.opener.isOpen) {
			closing.close();
		} else {
			closing.on('openingAnimationEnd', () => closing.close());
		}
	}

	// Leaving the page with the viewer open must not strand its overlay on <body>.
	$effect(() => {
		return () => closeViewer();
	});

	function createViewer(index: number) {
		const pswp = new PhotoSwipe({
			dataSource: maps.map((map, i) => toSlide(map, thumbnails[i])),
			index,
			// Solid, like a native photo viewer: at PhotoSwipe's default 0.8 the page
			// title and bottom nav show through behind the edge-to-edge map. Dragging
			// the map down to close still fades it and reveals the page.
			bgOpacity: 1,
			closeTitle: 'Закрыть',
			zoomTitle: 'Масштаб',
			arrowPrevTitle: 'Предыдущая карта',
			arrowNextTitle: 'Следующая карта',
			errorMsg: 'Не удалось загрузить карту',
			indexIndicatorSep: ' из '
		});
		pswp.on('uiRegister', () => pswp.ui?.registerElement(downloadButton));
		pswp.on('afterInit', () => localizeAria(pswp.element));
		pswp.on('close', () => {
			if (viewer !== pswp) return;
			// Closed from inside the viewer (button, Escape, swipe or pinch to close):
			// drop its history entry too, so back then leaves the page as expected.
			viewer = null;
			history.back();
		});
		pswp.init();
		return pswp;
	}

	// PhotoSwipe renders a bare <img srcset> rather than a <picture>, so it takes a
	// single format. WebP decodes on every browser the app supports; AVIF would
	// leave out iOS before 16 (https://caniuse.com/avif). As the user zooms,
	// PhotoSwipe raises the <img>'s `sizes`, so the browser fetches wider variants
	// up to the original — the map's labels stay sharp at full zoom.
	function toSlide(map: MapEntry, thumbnail: HTMLButtonElement | undefined): SlideData {
		const thumbnailImage = thumbnail?.querySelector('img');
		return {
			src: map.picture.img.src,
			srcset: map.picture.sources.webp,
			width: map.picture.img.w,
			height: map.picture.img.h,
			alt: map.alt,
			// Shown while the full image loads; the thumbnail's variant is already cached.
			msrc: thumbnailImage?.currentSrc,
			element: thumbnail
		};
	}

	// Downloads the original-format fallback (img.src, the largest variant).
	// The icon path is PhotoSwipe's own download-button example, so it matches the
	// built-in toolbar icons: https://photoswipe.com/adding-ui-elements/
	const downloadButton: UIElementData = {
		name: 'download-button',
		title: 'Скачать карту',
		order: 8,
		isButton: true,
		tagName: 'a',
		html: {
			isCustomSVG: true,
			inner:
				'<path d="M20.5 14.3 17.1 18V10h-2.2v7.9l-3.4-3.6L10 16l6 6.1 6-6.1ZM23 23H9v2h14Z" id="pswp__icn-download"/>',
			outlineID: 'pswp__icn-download'
		},
		onInit: (element, pswp) => {
			pswp.on('change', () => {
				const map = maps[pswp.currIndex];
				if (!map) return;
				element.setAttribute('href', map.picture.img.src);
				element.setAttribute('download', map.filename);
			});
		}
	};

	// PhotoSwipe gives its root role="dialog" without a name or aria-modal, and
	// hardcodes English role descriptions that screen readers read aloud.
	function localizeAria(root: HTMLElement | undefined) {
		if (!root) return;
		root.setAttribute('aria-modal', 'true');
		root.setAttribute('aria-label', 'Просмотр карты');
		for (const element of root.querySelectorAll('[aria-roledescription="carousel"]')) {
			element.setAttribute('aria-roledescription', 'карусель');
		}
		for (const element of root.querySelectorAll('[aria-roledescription="slide"]')) {
			element.setAttribute('aria-roledescription', 'слайд');
		}
	}
</script>

<svelte:head>
	<title>Карта фестиваля · ФАН ФАН</title>
</svelte:head>

<SectionIntro description="Нажми на карту, чтобы открыть её на весь экран." />

<!-- Stacked on mobile, side by side from lg so the now-portrait maps sit next to
each other on desktop. items-start keeps each frame at its own height. -->
<div class="grid items-start gap-4 lg:grid-cols-2">
	{#each maps as map, index (map.id)}
		<!-- w-fit makes the frame hug the image so a portrait map is centred without
		side letterboxing; the image sizes to its intrinsic ratio, capped to the
		container width and 70dvh so a tall map never overflows the viewport. -->
		<button
			bind:this={thumbnails[index]}
			type="button"
			onclick={() => openMap(index)}
			class="mx-auto block w-fit max-w-full overflow-hidden rounded-2xl border bg-muted p-2 shadow-sm transition-colors hover:bg-muted/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
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
			class="rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground lg:col-span-2"
		>
			Карты пока не добавлены.
		</div>
	{/each}
</div>

<style>
	/* PhotoSwipe appends its root to <body>, outside this component, hence :global. */
	:global(.pswp) {
		/* On the app's ladder rather than PhotoSwipe's 100000: above the bottom nav
		and every other overlay, like any fullscreen viewer. */
		--pswp-root-z-index: var(--z-modal);
	}

	/* app.html opts into viewport-fit=cover, so the overlay runs under the notch
	and rounded corners; keep the toolbar out from under them. */
	:global(.pswp__top-bar) {
		top: env(safe-area-inset-top);
		right: env(safe-area-inset-right);
		left: env(safe-area-inset-left);
		width: auto;
	}
</style>
