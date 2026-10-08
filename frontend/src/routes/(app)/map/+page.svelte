<script lang="ts">
	import type { Bounds, SlideData, UIElementData } from 'photoswipe';

	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Maximize2 } from '@lucide/svelte';
	import PhotoSwipe from 'photoswipe';

	import type { MapEntry } from '#lib/data/maps.js';

	import { maps } from '#lib/data/maps.js';
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
		void goto('', { shallow: true, state: { mapViewerIndex: index } });
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
		pswp.addFilter('thumbBounds', alignCropToTop);
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
			element: thumbnail,
			thumbCropped: true
		};
	}

	// The thumbnails crop to the top of the map (object-top), where the floor plan
	// sits; PhotoSwipe computes a cropped thumbnail as if centred. Shift its bounds
	// so the open and close animations line up with what the thumbnail shows.
	// `innerRect.y` is the image's offset inside the crop: 0 when top-aligned.
	function alignCropToTop(bounds: Bounds | undefined): Bounds {
		// The filter's type promises Bounds, but PhotoSwipe passes undefined when it
		// finds no thumbnail (and then fades instead); hand that back unchanged.
		if (!bounds?.innerRect) return bounds as Bounds;
		return {
			...bounds,
			y: bounds.y - bounds.innerRect.y,
			innerRect: { ...bounds.innerRect, y: 0 }
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
	<title>Карта · ФАН ФАН</title>
</svelte:head>

<!-- Two columns at every width, so both floors are on screen at once, with no
scrolling to find out the second one exists. A thumbnail at this size can't show
the legend legibly anyway: it is a door into the viewer, so it crops to the top of
the map, where the floor plan is, and the caption names the floor. 16:15 ends just
below the plan on the current posters, before their legend starts. -->
<div class="grid grid-cols-2 items-start gap-3 sm:gap-4">
	{#each maps as map, index (map.id)}
		<button
			bind:this={thumbnails[index]}
			type="button"
			onclick={() => openMap(index)}
			class="group flex flex-col gap-2 overflow-hidden rounded-2xl border bg-muted p-2 text-start shadow-sm transition-colors hover:bg-muted/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
			aria-haspopup="dialog"
			aria-label={`${map.label}\u00A0— открыть карту на весь экран`}
		>
			<span class="relative block">
				<enhanced:img
					src={map.picture}
					alt=""
					loading="lazy"
					sizes="(min-width: 1024px) 512px, 50vw"
					class="block aspect-[16/15] w-full rounded-xl object-cover object-top"
				/>
				<span
					class="absolute end-2 bottom-2 flex size-8 items-center justify-center rounded-full bg-black/60 text-white"
					aria-hidden="true"
				>
					<Maximize2 class="size-4" />
				</span>
			</span>
			<span class="px-1 pb-1 font-medium">{map.label}</span>
		</button>
	{:else}
		<div
			class="col-span-2 rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground"
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
