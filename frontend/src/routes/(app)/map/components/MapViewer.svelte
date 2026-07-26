<script lang="ts">
	import type { PanzoomEventDetail, PanzoomObject } from '@panzoom/panzoom';

	import Panzoom from '@panzoom/panzoom';
	import {
		ChevronLeftOutline,
		ChevronRightOutline,
		CloseOutline,
		DownloadOutline,
		ZoomInOutline,
		ZoomOutOutline
	} from 'flowbite-svelte-icons';
	import { prefersReducedMotion } from 'svelte/motion';

	import type { MapEntry } from '../maps';

	interface Props {
		// The map on screen. Bindable so the prev/next controls keep the caller's
		// selection in step instead of forking a second source of truth.
		entry: MapEntry;
		maps: MapEntry[];
		onclose: () => void;
	}

	let { entry = $bindable(), maps, onclose }: Props = $props();

	// Zooming past the image's own resolution only magnifies compression
	// artefacts, so the ceiling is measured from the file (see applyMaxScale).
	// The floor keeps desktop usable, where the map already renders near 1:1.
	const MIN_MAX_SCALE = 2.5;
	const MAX_MAX_SCALE = 6;
	const DOUBLE_TAP_SCALE = 2.5;

	// Anything above this counts as zoomed in — not exactly 1, because
	// focal-point zooming lands on values like 1.0000000002.
	const ZOOMED_IN_ABOVE = 1.01;

	const DOUBLE_TAP_MS = 300;
	// A tap that drifts further than this was a pan, not a tap.
	const TAP_SLOP_PX = 12;

	// Deliberately not $state: nothing in the template reads them, and keeping them
	// plain removes the hazard that broke this component once already — an
	// attachment that reads the same state it assigns re-runs itself, tearing down
	// the live panzoom instance and taking its event listeners with it.
	let panzoom: null | PanzoomObject = null;
	let image: HTMLImageElement | null = null;
	let stage: HTMLDivElement | null = null;

	let scale = $state(1);
	let maxScale = $state(MIN_MAX_SCALE);

	let index = $derived(maps.findIndex((candidate) => candidate.id === entry.id));
	let isZoomedIn = $derived(scale > ZOOMED_IN_ABOVE);
	let zoomLabel = $derived(isZoomedIn ? `${scale.toFixed(1)}×` : '1×');
	// A grab cursor at fit scale would promise panning that panOnlyWhenZoomed denies.
	let imageCursor = $derived(isZoomedIn ? 'cursor-grab active:cursor-grabbing' : 'cursor-zoom-in');

	function clamp(value: number, min: number, max: number) {
		return Math.min(Math.max(value, min), max);
	}

	// Panzoom's transform is `scale(s) translate(x, y)` about the element centre,
	// so pan values are in pre-scale pixels: the image may travel half of its
	// overhang past the viewport, divided by the scale.
	function snapIntoBounds(options: { animate: boolean }) {
		if (!panzoom || !image || !stage) return;

		const current = panzoom.getScale();
		const rendered = image.getBoundingClientRect();
		const viewport = stage.getBoundingClientRect();
		const limitX = Math.max(0, (rendered.width - viewport.width) / (2 * current));
		const limitY = Math.max(0, (rendered.height - viewport.height) / (2 * current));

		const { x, y } = panzoom.getPan();
		// force overrides panOnlyWhenZoomed, which otherwise makes pan() a no-op at
		// fit scale — leaving the map stuck off-centre after a pinch back to 1×.
		// pan() still no-ops when the clamped values are unchanged, so a gesture
		// that stayed in bounds costs nothing here.
		panzoom.pan(clamp(x, -limitX, limitX), clamp(y, -limitY, limitY), {
			...options,
			force: true
		});
	}

	// The ceiling is the image's pixel density against its fitted size, so a phone
	// (a 1280px file fitted to ~390px) can zoom to native pixels and no further.
	// Takes its subjects as arguments so it is safe to call from inside the
	// attachment, where reading component state would create a false dependency.
	function applyMaxScale(node: HTMLImageElement, instance: PanzoomObject) {
		if (!node.naturalWidth) return;

		// getBoundingClientRect() reports the transformed size; undo the scale to
		// recover the layout width the fit is based on.
		const fittedWidth = node.getBoundingClientRect().width / instance.getScale();
		if (fittedWidth === 0) return;

		const ceiling = clamp(node.naturalWidth / fittedWidth, MIN_MAX_SCALE, MAX_MAX_SCALE);
		maxScale = ceiling;
		instance.setOptions({ maxScale: ceiling });
	}

	// Re-measured on load and on resize, because the fit changes with the viewport.
	function refreshMaxScale() {
		if (panzoom && image) {
			applyMaxScale(image, panzoom);
		}
	}

	function bindPanzoom(node: HTMLImageElement) {
		const instance = Panzoom(node, {
			animate: true,
			// Let CSS own the cursor: panzoom writes an inline style that would
			// otherwise outrank the class swapped by `imageCursor`.
			cursor: '',
			duration: prefersReducedMotion.current ? 0 : 200,
			maxScale: MIN_MAX_SCALE,
			// Below the fit scale there is nothing to gain — a pinch-out would just
			// shrink the map into a thumbnail floating in black.
			minScale: 1,
			// A map fitted to the viewport has nothing to reveal by panning; moving
			// it would only drag it off-screen.
			panOnlyWhenZoomed: true,
			step: 0.4
			// Panzoom's own `contain` is unusable for a fitted image: 'outside'
			// raises minScale until the image covers the viewport (cropping a wide
			// map on a tall phone) and 'inside' caps maxScale at the fit scale
			// (no zoom at all). snapIntoBounds() enforces the edges instead.
		});

		const onChange = (event: Event) => {
			scale = (event as CustomEvent<PanzoomEventDetail>).detail.scale;
		};
		// Bounds are applied when the gesture ends rather than on every frame, so a
		// drag may overshoot and spring back the way native photo viewers do.
		const onEnd = () => snapIntoBounds({ animate: true });

		node.addEventListener('panzoomchange', onChange);
		node.addEventListener('panzoomend', onEnd);
		// The tap handlers are bound here rather than as onpointerdown/onpointerup
		// in the markup because Svelte delegates both events to the app root, and
		// panzoom's default handleStartEvent calls stopPropagation() on pointerdown
		// — so a delegated handler would never see the first half of a double tap.
		// A listener on the element itself is unaffected: stopPropagation() blocks
		// other nodes, not other listeners on this one.
		node.addEventListener('pointerdown', handlePointerDown);
		node.addEventListener('pointerup', handlePointerUp);

		// Tracked here rather than with bind:this so the element and its panzoom
		// instance are never briefly out of step while the {#key} block swaps maps.
		panzoom = instance;
		image = node;
		applyMaxScale(node, instance);

		return () => {
			node.removeEventListener('panzoomchange', onChange);
			node.removeEventListener('panzoomend', onEnd);
			node.removeEventListener('pointerdown', handlePointerDown);
			node.removeEventListener('pointerup', handlePointerUp);
			instance.destroy();
			panzoom = null;
			image = null;
			scale = 1;
		};
	}

	function openModal(node: HTMLDialogElement) {
		node.showModal();
		// Closing on teardown keeps the browser from stranding a removed dialog in
		// the top layer.
		return () => node.close();
	}

	function zoomIn() {
		panzoom?.zoomIn();
		snapIntoBounds({ animate: true });
	}

	function zoomOut() {
		panzoom?.zoomOut();
		snapIntoBounds({ animate: true });
	}

	function resetZoom() {
		panzoom?.reset();
	}

	function show(offset: number) {
		const next = maps[index + offset];
		if (next) entry = next;
	}

	function handleWheel(event: WheelEvent) {
		panzoom?.zoomWithWheel(event);
		// Not animated: a transition restarted on every wheel tick reads as lag.
		snapIntoBounds({ animate: false });
	}

	// Bound to the window rather than to the dialog: clicking a control that then
	// disables itself (reset at 1×, next on the last map) drops focus to <body>,
	// and a handler on the dialog would stop seeing keys from that point on.
	// Escape is left to the dialog itself — intercepting it would double-close.
	function handleKeydown(event: KeyboardEvent) {
		switch (event.key) {
			case '+':
			case '=':
				zoomIn();
				break;
			case '-':
				zoomOut();
				break;
			case '0':
				resetZoom();
				break;
			case 'ArrowLeft':
				show(-1);
				break;
			case 'ArrowRight':
				show(1);
				break;
			default:
				return;
		}
		event.preventDefault();
	}

	let tapStart: null | { x: number; y: number } = null;
	let lastTapAt = 0;

	function handlePointerDown(event: PointerEvent) {
		tapStart = event.isPrimary ? { x: event.clientX, y: event.clientY } : null;
	}

	// Double-tap toggles zoom, rolled by hand rather than with `ondblclick`:
	// panzoom sets `touch-action: none`, and browsers stop synthesising dblclick
	// from a touch double-tap once it is off. The same path serves mouse
	// double-clicks.
	function handlePointerUp(event: PointerEvent) {
		const start = tapStart;
		tapStart = null;
		if (!start || !event.isPrimary) return;

		const drift = Math.hypot(event.clientX - start.x, event.clientY - start.y);
		if (drift > TAP_SLOP_PX) return;

		if (event.timeStamp - lastTapAt < DOUBLE_TAP_MS) {
			lastTapAt = 0;
			toggleZoomAt(event);
			return;
		}
		lastTapAt = event.timeStamp;
	}

	function toggleZoomAt(point: PointerEvent) {
		if (!panzoom) return;

		if (isZoomedIn) {
			panzoom.reset();
			return;
		}
		panzoom.zoomToPoint(DOUBLE_TAP_SCALE, point);
		snapIntoBounds({ animate: true });
	}

	// A tap on the black around the map closes the viewer — but only at fit scale:
	// while zoomed in, a stray tap must not throw away what the user was reading.
	// The handler sits on the dialog rather than on a full-size backdrop button
	// because showModal() focuses the first focusable descendant, and an invisible
	// button there would swallow the opening focus.
	function handleSurfaceClick(event: MouseEvent) {
		if (event.target === stage && !isZoomedIn) {
			onclose();
		}
	}
</script>

<!-- No z-index: showModal() puts the dialog in the top layer, above the whole
	stacking ladder in docs/frontend.md regardless of z-*. Native <dialog> also
	brings the focus trap, Escape handling and background inertness for free,
	which is why this one screen does not use Flowbite's <Modal>. The surface is
	deliberately dark in both themes, the way every photo viewer is — that is the
	exception to the "always ship a dark: variant" rule, not a missing variant. -->
<dialog
	{@attach openModal}
	class="h-dvh max-h-none w-dvw max-w-none overscroll-contain border-0 bg-gray-950 p-0 text-white backdrop:bg-gray-950"
	onclick={handleSurfaceClick}
	{onclose}
	aria-label="Просмотр карты"
>
	<div
		bind:this={stage}
		onwheel={handleWheel}
		class="flex h-full w-full items-center justify-center overflow-hidden"
	>
		<!-- Keyed so switching maps rebuilds the element: the attachment re-runs,
			which resets the zoom and drops the previous image's decoded frame. -->
		{#key entry.id}
			<img
				{@attach bindPanzoom}
				src={entry.src}
				alt={entry.alt}
				width={entry.width}
				height={entry.height}
				onload={refreshMaxScale}
				draggable="false"
				class={['relative h-auto max-h-full w-auto max-w-full select-none', imageCursor]}
			/>
		{/key}
	</div>

	<!-- Chrome floats over the map so the image itself stays edge to edge; the
		wrappers stay pointer-transparent so the gaps between controls still close
		the viewer. The safe-area insets clear the iOS notch and home indicator when
		the PWA runs standalone. -->
	<div
		class="pointer-events-none absolute inset-x-0 top-0 flex items-center gap-2 p-3 pt-[max(0.75rem,env(safe-area-inset-top))]"
	>
		<p
			class="flex h-11 max-w-[60%] items-center truncate rounded-xl bg-gray-900/80 px-3 text-sm font-medium"
		>
			{entry.label}
		</p>

		<div class="pointer-events-auto ms-auto flex items-center gap-2">
			<a
				href={entry.src}
				download={entry.filename}
				rel="external"
				class="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900/80 transition-colors hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Скачать карту"
			>
				<DownloadOutline class="h-5 w-5" />
			</a>
			<button
				type="button"
				onclick={onclose}
				class="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900/80 transition-colors hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Закрыть"
			>
				<CloseOutline class="h-5 w-5" />
			</button>
		</div>
	</div>

	<div
		class="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-center gap-2 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
	>
		{#if maps.length > 1}
			<button
				type="button"
				onclick={() => show(-1)}
				disabled={index <= 0}
				class="pointer-events-auto flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900/80 transition-colors hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:opacity-40 disabled:hover:bg-gray-900/80"
				aria-label="Предыдущая карта"
			>
				<ChevronLeftOutline class="h-5 w-5" />
			</button>
		{/if}

		<div class="pointer-events-auto flex items-center rounded-xl bg-gray-900/80">
			<button
				type="button"
				onclick={zoomOut}
				disabled={!isZoomedIn}
				class="flex h-11 w-11 items-center justify-center rounded-xl transition-colors hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:opacity-40 disabled:hover:bg-transparent"
				aria-label="Уменьшить"
			>
				<ZoomOutOutline class="h-5 w-5" />
			</button>
			<button
				type="button"
				onclick={resetZoom}
				disabled={!isZoomedIn}
				class="h-11 min-w-14 rounded-xl text-xs font-medium tabular-nums transition-colors hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:hover:bg-transparent"
				aria-label="Сбросить масштаб"
			>
				{zoomLabel}
			</button>
			<button
				type="button"
				onclick={zoomIn}
				disabled={scale >= maxScale}
				class="flex h-11 w-11 items-center justify-center rounded-xl transition-colors hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:opacity-40 disabled:hover:bg-transparent"
				aria-label="Увеличить"
			>
				<ZoomInOutline class="h-5 w-5" />
			</button>
		</div>

		{#if maps.length > 1}
			<button
				type="button"
				onclick={() => show(1)}
				disabled={index >= maps.length - 1}
				class="pointer-events-auto flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900/80 transition-colors hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:opacity-40 disabled:hover:bg-gray-900/80"
				aria-label="Следующая карта"
			>
				<ChevronRightOutline class="h-5 w-5" />
			</button>
		{/if}
	</div>
</dialog>

<svelte:window onkeydown={handleKeydown} onresize={refreshMaxScale} />

<style>
	/* CSS-only, so the global prefers-reduced-motion rule in app.css shortens it
		without needing prefersReducedMotion here. */
	dialog {
		animation: viewer-in 200ms ease-out;
	}

	@keyframes viewer-in {
		from {
			opacity: 0;
			transform: scale(0.98);
		}
	}
</style>
