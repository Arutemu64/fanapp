<script lang="ts">
	import { Card } from 'flowbite-svelte';
	import {
		CalendarWeekOutline,
		MapPinAltOutline,
		ThumbsUpOutline,
		TicketOutline
	} from 'flowbite-svelte-icons';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
</script>

<svelte:head>
	<title>ФАН ФАН — главная</title>
</svelte:head>

<SectionHeader
	title="ФАН ФАН 2026"
	description="Коротко о фестивале и о том, чем приложение поможет во время мероприятия."
/>

<div class="space-y-4 sm:space-y-6">
	<!-- Этот блок даёт посетителю короткую памятку о фестивале ещё до перехода в разделы приложения. -->
	<div class="mx-auto max-w-5xl">
		<Card class="w-full max-w-none p-4 shadow-sm sm:p-6 lg:p-7">
			<div
				class="space-y-4 lg:grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:items-start lg:gap-6 lg:space-y-0"
			>
				<div class="space-y-2">
					<p class="text-sm font-semibold text-primary-700 dark:text-primary-400">
						Главное о фестивале
					</p>
					<h2 class="text-lg font-semibold text-gray-900 sm:text-xl lg:text-2xl dark:text-white">
						22 августа 2026 · ДК ГАЗ
					</h2>
					<p
						class="max-w-2xl text-sm leading-relaxed text-gray-600 sm:text-base dark:text-gray-300"
					>
						ФАН ФАН — фестиваль анимации, фантастики и косплея в Нижнем Новгороде. На площадке будут
						сценическая программа, фотозоны, игровые активности и ярмарка для поклонников аниме, игр
						и поп-культуры.
					</p>
				</div>

				<div class="grid gap-3 sm:grid-cols-2">
					<div
						class="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/70"
					>
						<p class="text-xs font-medium tracking-wide text-gray-500 uppercase dark:text-gray-400">
							Когда
						</p>
						<p class="mt-1 text-sm font-semibold text-gray-900 dark:text-white">22 августа 2026</p>
					</div>
					<div
						class="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/70"
					>
						<p class="text-xs font-medium tracking-wide text-gray-500 uppercase dark:text-gray-400">
							Где
						</p>
						<p class="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
							Нижний Новгород, ул. Героя Смирнова, 12
						</p>
					</div>
					<div
						class="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/70"
					>
						<p class="text-xs font-medium tracking-wide text-gray-500 uppercase dark:text-gray-400">
							Старт программы
						</p>
						<p class="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
							11:30, вход с 10:30
						</p>
					</div>
					<div
						class="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/70"
					>
						<p class="text-xs font-medium tracking-wide text-gray-500 uppercase dark:text-gray-400">
							Полезно знать
						</p>
						<p class="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
							Дети до 12 лет проходят бесплатно со взрослыми
						</p>
					</div>
				</div>
			</div>
		</Card>
	</div>

	<section aria-labelledby="home-features-heading" class="mx-auto max-w-6xl space-y-3">
		<div class="max-w-3xl space-y-1">
			<h2 id="home-features-heading" class="text-lg font-semibold text-gray-900 dark:text-white">
				Что можно сделать в приложении
			</h2>
			<p class="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
				Выбери нужный раздел, чтобы быстро найти программу, карту площадки и личные настройки.
			</p>
		</div>

		<!-- Эти карточки одновременно объясняют возможности приложения и работают как быстрые ссылки. -->
		<div id="home-nav-grid" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 lg:gap-3.5">
			<Card
				id="card-schedule"
				href="/schedule"
				class="group h-full w-full max-w-none py-4 shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50/40 dark:hover:border-primary-500 dark:hover:bg-primary-900/10"
			>
				<div class="flex flex-col items-center p-1 text-center sm:p-2">
					<div
						class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary-50 sm:mb-3 sm:h-12 sm:w-12 dark:bg-primary-900/30"
					>
						<CalendarWeekOutline
							class="h-5 w-5 text-primary-600 sm:h-6 sm:w-6 dark:text-primary-400"
						/>
					</div>
					<h3
						class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white"
					>
						Расписание
					</h3>
					<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">
						Ищи номера, следи за текущими событиями и проверяй изменения программы
					</p>
				</div>
			</Card>

			<Card
				id="card-map"
				href="/map"
				class="group h-full w-full max-w-none py-4 shadow-sm transition-colors hover:border-amber-300 hover:bg-amber-50/40 dark:hover:border-amber-500 dark:hover:bg-amber-900/10"
			>
				<div class="flex flex-col items-center p-1 text-center sm:p-2">
					<div
						class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 sm:mb-3 sm:h-12 sm:w-12 dark:bg-amber-900/30"
					>
						<MapPinAltOutline class="h-5 w-5 text-amber-600 sm:h-6 sm:w-6 dark:text-amber-400" />
					</div>
					<h3
						class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white"
					>
						Карта площадки
					</h3>
					<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">
						Открой схемы этажей и быстрее найди сцену, ярмарку и нужные зоны
					</p>
				</div>
			</Card>

			<Card
				id="card-voting"
				href="/voting"
				class="group h-full w-full max-w-none py-4 shadow-sm transition-colors hover:border-green-300 hover:bg-green-50/40 dark:hover:border-green-500 dark:hover:bg-green-900/10"
			>
				<div class="flex flex-col items-center p-1 text-center sm:p-2">
					<div
						class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-green-50 sm:mb-3 sm:h-12 sm:w-12 dark:bg-green-900/30"
					>
						<ThumbsUpOutline class="h-5 w-5 text-green-600 sm:h-6 sm:w-6 dark:text-green-400" />
					</div>
					<h3
						class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white"
					>
						Голосование
					</h3>
					<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">
						Выбирай номинации и поддерживай участников фестиваля своими голосами
					</p>
				</div>
			</Card>

			<!-- В профиле уже есть готовый сценарий привязки билета, поэтому ведём именно туда. -->
			<Card
				id="card-profile"
				href="/profile"
				class="group h-full w-full max-w-none py-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50/40 dark:hover:border-blue-500 dark:hover:bg-blue-900/10"
			>
				<div class="flex flex-col items-center p-1 text-center sm:p-2">
					<div
						class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 sm:mb-3 sm:h-12 sm:w-12 dark:bg-blue-900/30"
					>
						<TicketOutline class="h-5 w-5 text-blue-600 sm:h-6 sm:w-6 dark:text-blue-400" />
					</div>
					<h3
						class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white"
					>
						Профиль и билет
					</h3>
					<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">
						Привяжи билет, включи уведомления и установи приложение на главный экран
					</p>
				</div>
			</Card>
		</div>
	</section>
</div>
