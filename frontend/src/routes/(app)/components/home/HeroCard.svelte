<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { documentVisibility } from '$lib/services/documentVisibility';
	import { formatFestivalDateTime, pluralize } from '$lib/utils/formatters';
	import { prefersReducedMotion } from 'svelte/motion';

	import type { FestivalPhase } from './festivalPhase';

	interface Props {
		phase: FestivalPhase;
		festivalStart: string;
	}

	let { phase, festivalStart }: Props = $props();

	// Program start, on the venue clock. Configurable via GET /config and passed in
	// by the page so the hero renders for guests and on a cold/offline load.
	let startMs = $derived(new Date(festivalStart).getTime());
	let festivalDate = $derived(formatFestivalDateTime(festivalStart));

	let now = $state(Date.now());

	// Key art can fail to load on flaky con-venue wifi; drop it to bare the branded
	// bed instead of showing the browser's broken-image icon.
	let imageFailed = $state(false);

	let remaining = $derived(Math.max(0, startMs - now));

	const SECOND = 1000;
	const MINUTE = 60 * SECOND;
	const HOUR = 60 * MINUTE;
	const DAY = 24 * HOUR;

	let days = $derived(Math.floor(remaining / DAY));
	let hours = $derived(Math.floor((remaining % DAY) / HOUR));
	let minutes = $derived(Math.floor((remaining % HOUR) / MINUTE));
	let seconds = $derived(Math.floor((remaining % MINUTE) / SECOND));

	let units = $derived([
		{ id: 'days', value: days, label: pluralize(days, 'день', 'дня', 'дней') },
		{ id: 'hours', value: hours, label: pluralize(hours, 'час', 'часа', 'часов') },
		{ id: 'minutes', value: minutes, label: pluralize(minutes, 'минута', 'минуты', 'минут') },
		{ id: 'seconds', value: seconds, label: pluralize(seconds, 'секунда', 'секунды', 'секунд') }
	]);

	function pad(value: number): string {
		return value.toString().padStart(2, '0');
	}

	// The 1s ticker drives the visible countdown, so it only needs to run while we
	// are counting down to the start and the tab is in front — paused when hidden
	// because background timers aren't reliably throttled (an open SSE stream can
	// keep the tab awake). Svelte's guidance is to own timers in an $effect and
	// return their teardown; the interval is then cleared automatically when the
	// phase leaves 'before', the tab hides, or the component unmounts. Resyncing on
	// (re)entry keeps a return-from-hidden from painting a stale second. The phase
	// itself is the page's: it flips 'before' → 'during' on its own boundary timer.
	$effect(() => {
		if (phase !== 'before' || !documentVisibility.current) return;
		now = Date.now();
		const id = setInterval(() => (now = Date.now()), SECOND);
		return () => clearInterval(id);
	});
</script>

<!-- Shown before and after the festival only; during it the live programme leads
	 the page instead. The festival name is the page title in the top bar. -->
<section
	aria-labelledby="hero-heading"
	class="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-primary-900 via-gray-900 to-secondary-900 text-white shadow-sm"
>
	<!-- Key art as a backdrop. Decorative now that it carries no message of its
		 own, so alt="" — the dark brand bed underneath keeps the card readable while
		 the image streams in on weak con-venue wifi or if it fails to load at all. -->
	{#if !imageFailed}
		<!-- Static src, not a ?enhanced import: only the static-path form feeds
			 `sizes` back into the build, so it emits the full resized ladder — an
			 imported Picture would ship just 1x/2x widths. Output is still
			 content-hashed into `build`, which the service worker precaches, so
			 swapping the art busts every cache with no stale copy. LCP element:
			 eager + fetchpriority="high", never lazy.
			 `sizes` states the *cover* width, not the box width: `object-cover` scales
			 the 16/9 art to fill the box, and on a phone the after-festival panel
			 makes the box taller than 16/9, which upscales the art past 100vw. From
			 lg the card is capped by the page column (max-w-5xl). -->
		<enhanced:img
			src="./main.webp"
			alt=""
			sizes="(min-width: 1024px) 960px, 125vw"
			loading="eager"
			decoding="async"
			fetchpriority="high"
			onerror={() => (imageFailed = true)}
			class="absolute inset-0 -z-10 h-full w-full object-cover"
		/>
	{/if}
	<!-- Scrim: the photo is busy and bright in places, so white text needs a dark
		 layer under it to hold contrast wherever the crop lands. -->
	<div
		aria-hidden="true"
		class="absolute inset-0 -z-10 bg-gradient-to-t from-black/85 via-black/60 to-black/35"
	></div>

	<div class="flex flex-col gap-3 p-4 pt-16 sm:p-6 sm:pt-24">
		{#if phase === 'before'}
			<h2 id="hero-heading" class="text-xs font-semibold tracking-wide text-white/85 uppercase">
				До начала фестиваля
			</h2>
			<!-- Hide the live-ticking grid from screen readers; the static start date conveys it -->
			<div class="grid max-w-md grid-cols-4 gap-2" aria-hidden="true">
				{#each units as unit, index (unit.id)}
					<div
						class={[
							'countdown-cell flex flex-col items-center rounded-lg bg-white/15 px-1 py-2 backdrop-blur-sm',
							!prefersReducedMotion.current && 'countdown-cell--animated'
						]}
						style:--enter-delay="{index * 80}ms"
					>
						{#if prefersReducedMotion.current || unit.id === 'seconds'}
							<!-- Seconds change every tick; flipping them constantly is distracting -->
							<span class="font-display text-xl leading-none font-bold tabular-nums sm:text-2xl">
								{pad(unit.value)}
							</span>
						{:else}
							{#key unit.value}
								<span
									class="tick font-display text-xl leading-none font-bold tabular-nums sm:text-2xl"
								>
									{pad(unit.value)}
								</span>
							{/key}
						{/if}
						<span class="mt-1 text-xs text-white/85">
							{unit.label}
						</span>
					</div>
				{/each}
			</div>
			<p class="sr-only">Начало: {festivalDate}</p>
		{:else if phase === 'after'}
			<h2 id="hero-heading" class="text-lg font-semibold">Фестиваль завершён</h2>
			<p class="max-w-prose text-sm leading-relaxed text-white/85">
				Спасибо, что были с нами. До встречи в следующем году. Поделись впечатлениями — расскажи,
				как для тебя прошёл фестиваль.
			</p>
			<!-- Guests land on the auth-gated feedback page, which bounces them to
				 login and returns them here after (LOGIN_NEXT_PARAM). -->
			<Button href="/feedback" size="sm" class="self-start">Оставить отзыв</Button>
		{/if}
	</div>
</section>

<style>
	.countdown-cell--animated {
		animation: cell-enter 500ms cubic-bezier(0.22, 1, 0.36, 1) backwards;
		animation-delay: var(--enter-delay, 0ms);
	}

	.tick {
		display: inline-block;
		animation: tick-flip 450ms cubic-bezier(0.22, 1, 0.36, 1);
	}

	@keyframes cell-enter {
		from {
			opacity: 0;
			transform: translateY(12px) scale(0.96);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	@keyframes tick-flip {
		from {
			opacity: 0.3;
			transform: translateY(-40%);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.countdown-cell--animated,
		.tick {
			animation: none;
		}
	}
</style>
