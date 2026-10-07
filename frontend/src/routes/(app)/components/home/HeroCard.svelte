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

	// During the festival the live programme below is what people open the app
	// for, so the art shrinks to a banner and keeps it in the first screen.
	let artAspect = $derived(
		phase === 'during' ? 'aspect-[3/1] sm:aspect-[4/1]' : 'aspect-[16/9] sm:aspect-[4/3]'
	);

	let now = $state(Date.now());

	// Key art can fail to load on flaky con-venue wifi; fall back to a branded bed
	// instead of the browser's broken-image icon.
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

<section
	aria-labelledby="hero-title"
	class="relative overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
>
	<div class="relative grid lg:grid-cols-2 lg:items-stretch">
		<!-- Key art: full-bleed on top for mobile, full-bleed on the right for desktop.
			 The branded bed keeps the block meaningful while the heavy image streams
			 in on weak con-venue wifi, and replaces the broken-image icon if the art
			 fails to load at all. -->
		<div
			class={[
				'relative w-full overflow-hidden bg-gradient-to-br from-primary-100 via-primary-50 to-secondary-100 lg:order-2 lg:aspect-auto dark:from-primary-900/40 dark:via-background dark:to-secondary-900/40',
				artAspect
			]}
		>
			{#if imageFailed}
				<!-- Keep the alt available to screen readers even when the image is gone -->
				<span class="sr-only">Участники фестиваля ФАН ФАН на сцене</span>
				<div
					aria-hidden="true"
					class="absolute inset-0 flex items-center justify-center px-4 text-center"
				>
					<span
						class="font-display text-2xl font-bold text-primary-600/70 sm:text-3xl dark:text-primary-300/60"
					>
						ФАН ФАН
					</span>
				</div>
			{:else}
				<!-- Static src, not a ?enhanced import: only the static-path form feeds
					 `sizes` back into the build, so it emits the full resized ladder — an
					 imported Picture would ship just 1x/2x widths. Output is still
					 content-hashed into `build`, which the service worker precaches, so
					 swapping the art busts every cache with no stale copy. LCP element:
					 eager + fetchpriority="high", never lazy. width/height are injected
					 from the intrinsic size to prevent layout shift.
					 `sizes` below lg is the full-bleed width (100vw). From lg the column
					 is only ~480px wide, but `lg:aspect-auto` + `lg:items-stretch` let it
					 grow to the text column's full height (~500px) and `object-cover` then
					 scales the 16/9 art to cover that taller box — an effective render
					 width of ~500·16/9 ≈ 890px, not 480. `sizes` is width-only and can't
					 see that upscale, so it must state the *cover* width (~900px) or the
					 browser fetches a 480-target rung and paints it blurry on desktop. -->
				<enhanced:img
					src="./main.webp"
					alt="Участники фестиваля ФАН ФАН на сцене"
					sizes="(min-width: 1024px) 900px, 100vw"
					loading="eager"
					decoding="async"
					fetchpriority="high"
					onerror={() => (imageFailed = true)}
					class="h-full w-full object-cover"
				/>
			{/if}
		</div>

		<div class="flex flex-col gap-4 p-5 sm:p-7 lg:order-1 lg:p-9">
			<h1
				id="hero-title"
				class="font-display text-2xl leading-tight font-bold text-foreground sm:text-3xl lg:text-4xl"
			>
				ФАН ФАН 2026
			</h1>

			{#if phase === 'before'}
				<div
					aria-label="Обратный отсчёт до начала фестиваля"
					class="rounded-xl border border-primary-100 bg-primary-50/60 p-3 dark:border-primary-800/40 dark:bg-primary-900/20"
				>
					<p
						class="mb-2.5 text-xs font-medium tracking-wide text-primary-600 uppercase dark:text-primary-400"
					>
						До начала фестиваля
					</p>
					<!-- Hide the live-ticking grid from screen readers; the static start date conveys it -->
					<div class="grid grid-cols-4 gap-2" aria-hidden="true">
						{#each units as unit, index (unit.id)}
							<div
								class={[
									'countdown-cell flex flex-col items-center rounded-lg bg-card px-1 py-2.5 shadow-sm',
									!prefersReducedMotion.current && 'countdown-cell--animated'
								]}
								style:--enter-delay="{index * 80}ms"
							>
								{#if prefersReducedMotion.current || unit.id === 'seconds'}
									<!-- Seconds change every tick; flipping them constantly is distracting -->
									<span
										class="font-display text-xl leading-none font-bold text-foreground tabular-nums sm:text-2xl"
									>
										{pad(unit.value)}
									</span>
								{:else}
									{#key unit.value}
										<span
											class="tick font-display text-xl leading-none font-bold text-foreground tabular-nums sm:text-2xl"
										>
											{pad(unit.value)}
										</span>
									{/key}
								{/if}
								<span class="mt-1 text-xs text-muted-foreground">
									{unit.label}
								</span>
							</div>
						{/each}
					</div>
					<p class="sr-only">Начало: {festivalDate}</p>
				</div>
			{:else if phase === 'after'}
				<div class="rounded-xl border border-border bg-muted p-3">
					<p class="text-sm font-semibold text-foreground">Фестиваль завершён</p>
					<p class="mt-1 text-xs leading-5 text-muted-foreground">
						Спасибо, что были с нами. До встречи в следующем году.
					</p>
					<p class="mt-2 text-xs leading-5 text-muted-foreground">
						Поделись впечатлениями — расскажи, как для тебя прошёл фестиваль.
					</p>
					<!-- Guests land on the auth-gated feedback page, which bounces them to
						 login and returns them here after (LOGIN_NEXT_PARAM). -->
					<Button href="/feedback" size="sm" class="mt-3">Оставить отзыв</Button>
				</div>
			{/if}
		</div>
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
