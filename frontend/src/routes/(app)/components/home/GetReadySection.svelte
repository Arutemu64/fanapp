<script lang="ts">
	import type { Component } from 'svelte';
	import type { Pathname } from '$app/types';
	import UserPlusIcon from '~icons/lucide/user-plus';
	import DownloadIcon from '~icons/lucide/download';
	import TicketIcon from '~icons/lucide/ticket';
	import CalendarCheckIcon from '~icons/lucide/calendar-check';
	import BellIcon from '~icons/lucide/bell';
	import type { UserFullDTO } from '$lib/types/user';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import GetReadyCard from './GetReadyCard.svelte';

	interface Props {
		user: UserFullDTO | null;
	}

	let { user }: Props = $props();

	const pwa = getPwaService();

	interface ReadyCard {
		key: string;
		title: string;
		description: string;
		icon: Component;
		iconClass: string;
		hoverClass: string;
		href?: Pathname;
		onclick?: () => void;
	}

	const accent = {
		primary: {
			icon: 'bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
			hover:
				'hover:border-primary-300 hover:bg-primary-50/40 dark:hover:border-primary-500 dark:hover:bg-primary-900/10'
		},
		secondary: {
			icon: 'bg-secondary-50 text-secondary-600 dark:bg-secondary-900/30 dark:text-secondary-400',
			hover:
				'hover:border-secondary-300 hover:bg-secondary-50/40 dark:hover:border-secondary-500 dark:hover:bg-secondary-900/10'
		},
		amber: {
			icon: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
			hover:
				'hover:border-amber-300 hover:bg-amber-50/40 dark:hover:border-amber-500 dark:hover:bg-amber-900/10'
		},
		green: {
			icon: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400',
			hover:
				'hover:border-green-300 hover:bg-green-50/40 dark:hover:border-green-500 dark:hover:bg-green-900/10'
		},
		blue: {
			icon: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
			hover:
				'hover:border-blue-300 hover:bg-blue-50/40 dark:hover:border-blue-500 dark:hover:bg-blue-900/10'
		}
	};

	// Установку показываем, пока приложение не добавлено и платформа это поддерживает.
	let showPwa = $derived(!pwa.isInstalled && (pwa.canInstall || pwa.isIOS || pwa.isAndroid));

	let cards = $derived.by<ReadyCard[]>(() => {
		const list: ReadyCard[] = [];

		if (!user) {
			list.push({
				key: 'account',
				title: 'Создать аккаунт',
				description: 'Нужен для голосования и подписки на события программы.',
				icon: UserPlusIcon,
				iconClass: accent.primary.icon,
				hoverClass: accent.primary.hover,
				href: '/login'
			});
		}

		if (showPwa) {
			list.push({
				key: 'pwa',
				title: 'Установить приложение',
				description: 'Быстрый доступ с главного экрана и push-уведомления.',
				icon: DownloadIcon,
				iconClass: accent.secondary.icon,
				hoverClass: accent.secondary.hover,
				// Если установка доступна напрямую — запускаем её, иначе ведём в профиль с подсказкой.
				...(pwa.canInstall ? { onclick: () => pwa.install() } : { href: '/profile' })
			});
		}

		if (user && !user.ticket) {
			list.push({
				key: 'ticket',
				title: 'Привязать билет',
				description: 'Открывает голосование за участников фестиваля.',
				icon: TicketIcon,
				iconClass: accent.amber.icon,
				hoverClass: accent.amber.hover,
				href: '/profile'
			});
		}

		if (user) {
			list.push({
				key: 'schedule',
				title: 'Посмотреть программу',
				description: 'Подпишись на номера, чтобы не пропустить любимые события.',
				icon: CalendarCheckIcon,
				iconClass: accent.green.icon,
				hoverClass: accent.green.hover,
				href: '/schedule'
			});

			list.push({
				key: 'notifications',
				title: 'Настроить уведомления',
				description: 'Получай напоминания о начале событий и изменениях.',
				icon: BellIcon,
				iconClass: accent.blue.icon,
				hoverClass: accent.blue.hover,
				href: '/profile'
			});
		}

		return list;
	});
</script>

{#if cards.length > 0}
	<section aria-labelledby="get-ready-heading" class="space-y-3">
		<div class="max-w-3xl space-y-1">
			<h2 id="get-ready-heading" class="text-lg font-semibold text-gray-900 dark:text-white">
				Подготовься к фестивалю
			</h2>
			<p class="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
				Несколько шагов, чтобы получить максимум от приложения на мероприятии.
			</p>
		</div>

		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
			{#each cards as card (card.key)}
				<GetReadyCard
					title={card.title}
					description={card.description}
					icon={card.icon}
					iconClass={card.iconClass}
					hoverClass={card.hoverClass}
					href={card.href}
					onclick={card.onclick}
				/>
			{/each}
		</div>
	</section>
{/if}
