<script lang="ts">
	import { onMount } from 'svelte';
	import CalendarIcon from '~icons/mdi/calendar';
	import PinDropIcon from '~icons/material-symbols/pin-drop';
	import GlobeIcon from '~icons/lucide/globe';
	import TelegramIcon from '~icons/ic/baseline-telegram';
	import VkIcon from '~icons/ri/vk-fill';
	import TiktokIcon from '~icons/ic/baseline-tiktok';

	const socials = [
		{ label: 'Официальный сайт fancom.info', href: 'https://fancom.info', icon: GlobeIcon },
		{ label: 'Telegram', href: 'https://t.me/fanfan_fest_news', icon: TelegramIcon },
		{ label: 'ВКонтакте', href: 'https://vk.com/fan_fest', icon: VkIcon },
		{ label: 'TikTok', href: 'https://www.tiktok.com/@fan_fan_official', icon: TiktokIcon }
	];

	// Старт программы — 22 августа 2026, 11:30 по московскому времени (UTC+3).
	const TARGET = new Date('2026-08-22T11:30:00+03:00').getTime();

	let now = $state(Date.now());
	let prefersReducedMotion = $state(false);

	onMount(() => {
		const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
		prefersReducedMotion = motionQuery.matches;
		const onMotionChange = (e: MediaQueryListEvent) => {
			prefersReducedMotion = e.matches;
		};
		motionQuery.addEventListener('change', onMotionChange);

		const interval = setInterval(() => {
			now = Date.now();
		}, 1000);

		return () => {
			clearInterval(interval);
			motionQuery.removeEventListener('change', onMotionChange);
		};
	});

	let remaining = $derived(Math.max(0, TARGET - now));
	let hasStarted = $derived(remaining <= 0);

	const SECOND = 1000;
	const MINUTE = 60 * SECOND;
	const HOUR = 60 * MINUTE;
	const DAY = 24 * HOUR;

	let days = $derived(Math.floor(remaining / DAY));
	let hours = $derived(Math.floor((remaining % DAY) / HOUR));
	let minutes = $derived(Math.floor((remaining % HOUR) / MINUTE));
	let seconds = $derived(Math.floor((remaining % MINUTE) / SECOND));

	// Русское склонение единиц («1 день», «2 дня», «5 дней»).
	function plural(value: number, forms: [string, string, string]): string {
		const mod100 = value % 100;
		const mod10 = value % 10;
		if (mod100 >= 11 && mod100 <= 14) return forms[2];
		if (mod10 === 1) return forms[0];
		if (mod10 >= 2 && mod10 <= 4) return forms[1];
		return forms[2];
	}

	let units = $derived([
		{ id: 'days', value: days, label: plural(days, ['день', 'дня', 'дней']) },
		{ id: 'hours', value: hours, label: plural(hours, ['час', 'часа', 'часов']) },
		{ id: 'minutes', value: minutes, label: plural(minutes, ['минута', 'минуты', 'минут']) },
		{ id: 'seconds', value: seconds, label: plural(seconds, ['секунда', 'секунды', 'секунд']) }
	]);

	function pad(value: number): string {
		return value.toString().padStart(2, '0');
	}
</script>

<section
	aria-labelledby="hero-title"
	class="relative overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900"
>
	<!-- Атмосферное свечение по краям, декоративное -->
	<div
		aria-hidden="true"
		class="pointer-events-none absolute -top-24 -left-20 h-64 w-64 rounded-full bg-primary-200/40 blur-3xl dark:bg-primary-900/20"
	></div>

	<div class="relative grid lg:grid-cols-2 lg:items-stretch">
		<!-- Ключевой арт: сверху на мобильных (full-bleed), справа на десктопе (full-bleed) -->
		<div class="aspect-[16/9] w-full sm:aspect-[4/3] lg:order-2 lg:aspect-auto">
			<div
				class="relative flex h-full w-full items-center justify-center bg-gradient-to-br from-primary-500 via-primary-600 to-secondary-600"
			>
				<div
					aria-hidden="true"
					class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.35),transparent_55%)]"
				></div>
				<span class="font-display text-sm font-semibold tracking-wide text-white/80 uppercase">
					Key art
				</span>
			</div>
		</div>

		<!-- Текстовый блок -->
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

			{#if hasStarted}
				<dl>
					<div class="flex items-center gap-3">
						<span
							class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400"
						>
							<CalendarIcon class="h-5 w-5" aria-hidden="true" />
						</span>
						<div>
							<dt class="sr-only">Когда</dt>
							<dd class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
								22 августа 2026, 11:30
							</dd>
						</div>
					</div>
				</dl>
			{/if}

			{#if !hasStarted}
				<div
					aria-label="Обратный отсчёт до начала фестиваля"
					class="rounded-xl border border-primary-100 bg-primary-50/60 p-3 dark:border-primary-800/40 dark:bg-primary-900/20"
				>
					<p
						class="mb-2.5 text-xs font-medium tracking-wide text-primary-600/80 uppercase dark:text-primary-400/80"
					>
						До начала фестиваля
					</p>
					<div class="grid grid-cols-4 gap-2">
						{#each units as unit, index (unit.id)}
							<div
								class="countdown-cell flex flex-col items-center rounded-lg bg-white px-1 py-2.5 shadow-sm dark:bg-gray-800"
								class:countdown-cell--animated={!prefersReducedMotion}
								style:--enter-delay="{index * 80}ms"
							>
								{#if prefersReducedMotion}
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
								<span class="mt-1 text-[0.6rem] text-gray-400 dark:text-gray-500">
									{unit.label}
								</span>
							</div>
						{/each}
					</div>
					<p class="mt-2 text-xs text-gray-400 dark:text-gray-500">22 августа 2026 · 11:30</p>
				</div>
			{/if}

			<dl>
				<div class="flex items-center gap-3">
					<span
						class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary-50 text-secondary-600 dark:bg-secondary-900/30 dark:text-secondary-400"
					>
						<PinDropIcon class="h-5 w-5" aria-hidden="true" />
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
