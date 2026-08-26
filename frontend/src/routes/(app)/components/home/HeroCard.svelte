<script lang="ts">
	import { formatFestivalDateTime, pluralize } from '$lib/utils/formatters';
	import { Button } from 'flowbite-svelte';
	import {
		AnnotationOutline,
		CalendarMonthOutline,
		GlobeOutline,
		MapPinAltOutline
	} from 'flowbite-svelte-icons';
	import { prefersReducedMotion } from 'svelte/motion';
	import TelegramIcon from '~icons/simple-icons/telegram';
	import TiktokIcon from '~icons/simple-icons/tiktok';
	import VkIcon from '~icons/simple-icons/vk';

	let { festivalStart, festivalEnd }: { festivalStart: string; festivalEnd: string } = $props();

	const socials = [
		{ label: 'Официальный сайт fancom.info', href: 'https://fancom.info', icon: GlobeOutline },
		{ label: 'Telegram', href: 'https://t.me/fanfan_fest_news', icon: TelegramIcon },
		{ label: 'ВКонтакте', href: 'https://vk.ru/fan_fest', icon: VkIcon },
		{ label: 'TikTok', href: 'https://www.tiktok.com/@fan_fan_official', icon: TiktokIcon }
	];

	// Program start/end, on the venue clock. Configurable via GET /config and passed
	// in by the page so the hero renders for guests and on a cold/offline load.
	let startMs = $derived(new Date(festivalStart).getTime());
	let endMs = $derived(new Date(festivalEnd).getTime());
	let festivalDate = $derived(formatFestivalDateTime(festivalStart));

	let now = $state(Date.now());
	let documentVisible = $state(true);

	// Key art can fail to load on flaky con-venue wifi; fall back to a branded bed
	// instead of the browser's broken-image icon.
	let imageFailed = $state(false);

	let remaining = $derived(Math.max(0, startMs - now));

	// before → counting down to the start; during → the festival is running;
	// after → it has wrapped up. Both boundaries are instants, so the phase flips
	// on its own as `now` crosses them (see the ticker and boundary effects below);
	// there is no operator switch to forget to press.
	let phase = $derived.by(() => {
		if (now >= endMs) return 'after';
		if (now >= startMs) return 'during';
		return 'before';
	});

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
	// (re)entry keeps a return-from-hidden from painting a stale second, and lets
	// `now` cross `startMs` so the phase advances to 'during' on its own.
	$effect(() => {
		if (phase !== 'before' || !documentVisible) return;
		now = Date.now();
		const id = setInterval(() => (now = Date.now()), SECOND);
		return () => clearInterval(id);
	});

	// Flip 'during' → 'after' the moment festival_end passes. A single timeout to
	// the boundary beats a 1s interval ticking pointlessly through the whole
	// festival: it fires once, bumps `now`, and the phase derives the rest. Clamped
	// to 0 so an end already in the past resolves on the next frame.
	$effect(() => {
		if (phase !== 'during') return;
		// Delay off the live clock, not the `now` state, so this effect tracks only
		// phase and endMs — it schedules once on entering 'during' and never re-runs
		// on a tick.
		const id = setTimeout(() => (now = Date.now()), Math.max(0, endMs - Date.now()));
		return () => clearTimeout(id);
	});
</script>

<svelte:document
	onvisibilitychange={() => (documentVisible = document.visibilityState === 'visible')}
/>

<section
	aria-labelledby="hero-title"
	class="relative overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900"
>
	<div class="relative grid lg:grid-cols-2 lg:items-stretch">
		<!-- Key art: full-bleed on top for mobile, full-bleed on the right for desktop.
			 The branded bed keeps the block meaningful while the heavy image streams
			 in on weak con-venue wifi, and replaces the broken-image icon if the art
			 fails to load at all. -->
		<div
			class="relative aspect-[16/9] w-full overflow-hidden bg-gradient-to-br from-primary-100 via-primary-50 to-secondary-100 sm:aspect-[4/3] lg:order-2 lg:aspect-auto dark:from-primary-900/40 dark:via-gray-900 dark:to-secondary-900/40"
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

		<div class="space-y-4 p-5 sm:p-7 lg:order-1 lg:p-9">
			<div class="space-y-2">
				<h1
					id="hero-title"
					class="font-display text-2xl leading-tight font-bold text-gray-900 sm:text-3xl lg:text-4xl dark:text-white"
				>
					ФАН ФАН 2026
				</h1>
				<p
					class="max-w-prose text-sm leading-relaxed text-gray-600 sm:text-base dark:text-gray-300"
				>
					Добро пожаловать на главное событие года для всех поклонников косплея и популярной
					культуры в Нижнем Новгороде — фестиваль анимации и фантастики ФАН ФАН.
				</p>
			</div>

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
					<!-- Hide the live-ticking grid from screen readers; the static date below conveys it -->
					<div class="grid grid-cols-4 gap-2" aria-hidden="true">
						{#each units as unit, index (unit.id)}
							<div
								class={[
									'countdown-cell flex flex-col items-center rounded-lg bg-white px-1 py-2.5 shadow-sm dark:bg-gray-800',
									!prefersReducedMotion.current && 'countdown-cell--animated'
								]}
								style:--enter-delay="{index * 80}ms"
							>
								{#if prefersReducedMotion.current || unit.id === 'seconds'}
									<!-- Seconds change every tick; flipping them constantly is distracting -->
									<span
										class="font-display text-xl leading-none font-bold text-gray-900 tabular-nums sm:text-2xl dark:text-white"
									>
										{pad(unit.value)}
									</span>
								{:else}
									{#key unit.value}
										<span
											class="tick font-display text-xl leading-none font-bold text-gray-900 tabular-nums sm:text-2xl dark:text-white"
										>
											{pad(unit.value)}
										</span>
									{/key}
								{/if}
								<span class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									{unit.label}
								</span>
							</div>
						{/each}
					</div>
					<p class="mt-2 text-xs text-gray-600 dark:text-gray-400">{festivalDate}</p>
				</div>
			{:else if phase === 'during'}
				<div
					class="rounded-xl border border-primary-100 bg-primary-50/60 p-3 dark:border-primary-800/40 dark:bg-primary-900/20"
				>
					<p class="text-sm font-semibold text-primary-700 dark:text-primary-300">
						Фестиваль идёт прямо сейчас
					</p>
					<p class="mt-1 text-xs leading-5 text-gray-600 dark:text-gray-400">
						Загляни в программу, чтобы не пропустить ближайшие выступления.
					</p>
				</div>
			{:else}
				<div
					class="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60"
				>
					<p class="text-sm font-semibold text-gray-900 dark:text-white">Фестиваль завершён</p>
					<p class="mt-1 text-xs leading-5 text-gray-600 dark:text-gray-400">
						Спасибо, что были с нами. До встречи в следующем году.
					</p>
					<p class="mt-2 text-xs leading-5 text-gray-600 dark:text-gray-400">
						Поделись впечатлениями — расскажи, как для тебя прошёл фестиваль.
					</p>
					<!-- Guests land on the auth-gated feedback page, which bounces them to
						 login and returns them here after (LOGIN_NEXT_PARAM). -->
					<Button href="/feedback" color="primary" size="sm" class="mt-3">
						<AnnotationOutline class="me-2 h-4 w-4" aria-hidden="true" />
						Оставить отзыв
					</Button>
				</div>
			{/if}

			{#if phase !== 'before'}
				<dl>
					<div class="flex items-center gap-3">
						<span
							class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400"
						>
							<CalendarMonthOutline class="h-5 w-5" aria-hidden="true" />
						</span>
						<div>
							<dt class="sr-only">Когда</dt>
							<dd class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
								{festivalDate}
							</dd>
						</div>
					</div>
				</dl>
			{/if}

			<dl>
				<div class="flex items-center gap-3">
					<span
						class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary-50 text-secondary-600 dark:bg-secondary-900/30 dark:text-secondary-400"
					>
						<MapPinAltOutline class="h-5 w-5" aria-hidden="true" />
					</span>
					<div>
						<dt class="sr-only">Где</dt>
						<dd class="text-sm text-gray-600 sm:text-base dark:text-gray-300">
							<a
								href="https://yandex.ru/maps/-/CPXxrYIR"
								target="_blank"
								rel="noopener noreferrer"
								class="font-medium text-gray-900 underline decoration-secondary-400 decoration-2 underline-offset-2 transition-colors hover:text-secondary-600 dark:text-white dark:hover:text-secondary-400"
							>
								Нижний Новгород, ул. Героя Смирнова, 12, ДК «ГАЗ»
							</a>
						</dd>
					</div>
				</div>
			</dl>

			<div class="flex flex-wrap items-center gap-2 pt-1">
				{#each socials as social (social.href)}
					<a
						href={social.href}
						target="_blank"
						rel="noopener noreferrer external"
						aria-label={social.label}
						class="flex h-11 w-11 items-center justify-center rounded-xl border border-gray-200 bg-gray-50 text-gray-600 transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-primary-500 dark:hover:bg-primary-900/20 dark:hover:text-primary-400"
					>
						<social.icon class="h-5 w-5" aria-hidden="true" />
					</a>
				{/each}
			</div>
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
