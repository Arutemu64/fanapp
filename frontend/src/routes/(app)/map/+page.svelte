<script lang="ts">
	import type { MapEntry } from '$lib/data/maps';

	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { maps } from '$lib/data/maps';
	import Panzoom from '@panzoom/panzoom';
	import { CloseOutline, CompressOutline, DownloadOutline } from 'flowbite-svelte-icons';

	// Currently opened map for the fullscreen viewer, or null when closed.
	let active = $state<MapEntry | null>(null);

	// The live Panzoom instance for the open viewer, so the reset button can
	// reach it. Null while the viewer is closed. Reassigned by the attachment
	// below, which the {#if active} block recreates on every open — so each map
	// starts un-zoomed with no stale transform carried over.
	let panzoom = $state<ReturnType<typeof Panzoom> | null>(null);

	// Wire pinch/drag/wheel zoom onto the map image once the overlay mounts.
	// Panzoom transforms this element via CSS, so the enhanced:img markup is
	// untouched. No `contain`: it derives scale limits from the element-vs-parent
	// box and clamps zoom to ~1x here, defeating the feature. overflow:'visible'
	// (Panzoom defaults to 'hidden') lets the map grow past its frame as it scales
	// instead of being clipped inside it — the clip read as "scrolling inside a
	// card". Free panning is the trade; reset and double-tap recentre. The global
	// step stays at its 0.3 default: pinch gain is proportional to it, so lowering
	// it to soften the wheel would also slow pinch. The wheel gets its own step
	// per-call below instead, keeping the two gestures independent.
	function zoomable(element: HTMLElement) {
		const instance = Panzoom(element, {
			minScale: 1,
			maxScale: 6,
			overflow: 'visible'
		});
		panzoom = instance;
		// Wheel-to-zoom is opt-in in Panzoom; bind it to the scrolling container.
		// step is halved for the wheel only: Panzoom zooms one step per wheel *event*
		// regardless of delta, so trackpads (a burst per scroll) shoot to max at the
		// 0.3 default; 0.15 keeps a notch gentle without touching pinch.
		const parent = element.parentElement;
		const onWheel = (event: WheelEvent) => instance.zoomWithWheel(event, { step: 0.15 });
		parent?.addEventListener('wheel', onWheel);
		// Double-tap/double-click to reset — a pointer gesture shortcut for the
		// keyboard-accessible reset button in the controls. Bound here rather than
		// as a template handler so the target stays a non-interactive image.
		const reset = () => instance.reset();
		element.addEventListener('dblclick', reset);
		return () => {
			parent?.removeEventListener('wheel', onWheel);
			element.removeEventListener('dblclick', reset);
			instance.destroy();
			panzoom = null;
		};
	}

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
	<title>Карта фестиваля · ФАН ФАН</title>
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
	<!-- Fullscreen viewer overlay. Tap the backdrop or the close button to dismiss.
	     An inline (non-portaled) modal, so it takes the --z-modal rung to cover the
	     fixed bottom nav — see docs/frontend.md "Z-Index Scale". -->
	<div
		class="fixed inset-0 z-(--z-modal) flex items-center justify-center bg-black/80 p-4"
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

		<!-- Panzoom frame: the parent Panzoom measures for its wheel/pinch focal
		point, so it must hug the image with no gap. Panzoom assumes the zoom target
		sits at its parent's top-left; if the overlay's flex-centering were the only
		parent, the focal point would be off by the letterbox gap and zoom would
		drift sideways on a narrow portrait map. This frame is what the overlay
		centers instead, so parent and target share one box — but it does not clip
		(see overflow:'visible' in zoomable), so the map grows past it as it scales.
		Caps are viewport units, not max-h-full: enhanced:img wraps the <img> in an
		inline <picture> with no definite height, so a percentage max-height never
		resolves and a tall map overflows. 2rem matches the overlay's p-4. w-auto
		sizes to the intrinsic ratio and never upscales. touch-none must sit on the
		actual touch target (the <img>) and the zoom element, not only the frame:
		iOS Safari lets a gesture that starts on a touch-action:auto element fall
		through to native page pinch/scroll, which starves Panzoom of pointer events
		and kills zooming. double-tap resets the zoom. -->
		<div
			class="relative block h-fit max-h-[calc(100dvh-2rem)] w-fit max-w-[calc(100vw-2rem)] touch-none"
		>
			<div {@attach zoomable} class="block touch-none">
				<enhanced:img
					src={active.picture}
					alt={active.alt}
					sizes="(min-width: 1024px) 1024px, 100vw"
					class="block max-h-[calc(100dvh-2rem)] w-auto max-w-[calc(100vw-2rem)] touch-none rounded-xl shadow-2xl select-none"
				/>
			</div>
		</div>

		<div class="absolute end-4 top-4 z-10 flex items-center gap-2">
			<!-- Keyboard-accessible counterpart to double-tap: pinch/wheel have no key
			equivalent, so this is the only way to undo a zoom without a pointer. -->
			<button
				type="button"
				onclick={() => panzoom?.reset()}
				class="flex h-11 w-11 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Сбросить масштаб"
			>
				<CompressOutline class="h-6 w-6" />
			</button>
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
