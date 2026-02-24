<script lang="ts">
	import { Card } from 'flowbite-svelte';
	import { CalendarWeekOutline, ThumbsUpOutline, TicketOutline } from 'flowbite-svelte-icons';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
</script>

<svelte:head>
	<title>FAN App</title>
</svelte:head>

<SectionHeader title="Добро пожаловать!" description="Ваш персональный помощник на мероприятии" />

<div id="home-nav-grid" class="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
	<Card
		id="card-schedule"
		href="/schedule"
		class="group h-full py-4 transition-all duration-300 ease-out hover:-translate-y-1 hover:border-primary-400 hover:shadow-xl dark:hover:border-primary-500"
	>
		<div class="flex flex-col items-center p-1 text-center sm:p-2">
			<div
				class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary-50 transition-colors duration-300 group-hover:bg-primary-100 sm:mb-3 sm:h-12 sm:w-12 dark:bg-primary-900/30 dark:group-hover:bg-primary-900/50"
			>
				<CalendarWeekOutline
					class="h-5 w-5 text-primary-600 transition-transform duration-300 group-hover:scale-110 sm:h-6 sm:w-6 dark:text-primary-400"
				/>
			</div>
			<h2 class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white">
				Расписание
			</h2>
			<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">
				Следите за ходом мероприятия
			</p>
		</div>
	</Card>

	<Card
		id="card-voting"
		href="/voting"
		class="group h-full py-4 transition-all duration-300 ease-out hover:-translate-y-1 hover:border-green-400 hover:shadow-xl dark:hover:border-green-500"
	>
		<div class="flex flex-col items-center p-1 text-center sm:p-2">
			<div
				class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-green-50 transition-colors duration-300 group-hover:bg-green-100 sm:mb-3 sm:h-12 sm:w-12 dark:bg-green-900/30 dark:group-hover:bg-green-900/50"
			>
				<ThumbsUpOutline
					class="h-5 w-5 text-green-600 transition-transform duration-300 group-hover:scale-110 sm:h-6 sm:w-6 dark:text-green-400"
				/>
			</div>
			<h2 class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white">
				Голосование
			</h2>
			<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">
				Голосуйте за лучших участников
			</p>
		</div>
	</Card>

	<Card
		id="card-link-ticket"
		href="/link_ticket"
		class="group h-full py-4 transition-all duration-300 ease-out hover:-translate-y-1 hover:border-blue-400 hover:shadow-xl sm:col-span-2 lg:col-span-1 dark:hover:border-blue-500"
	>
		<div class="flex flex-col items-center p-1 text-center sm:p-2">
			<div
				class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 transition-colors duration-300 group-hover:bg-blue-100 sm:mb-3 sm:h-12 sm:w-12 dark:bg-blue-900/30 dark:group-hover:bg-blue-900/50"
			>
				<TicketOutline
					class="h-5 w-5 text-blue-600 transition-transform duration-300 group-hover:scale-110 sm:h-6 sm:w-6 dark:text-blue-400"
				/>
			</div>
			<h2 class="mb-0.5 text-sm font-semibold text-gray-900 sm:mb-1 sm:text-base dark:text-white">
				Привязать билет
			</h2>
			<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">Разблокируйте все функции</p>
		</div>
	</Card>
</div>
