<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { Component } from 'svelte';

	import { getPwaService } from '$lib/services/pwa.svelte';
	import { Bell, Calendar, Download, Ticket, UserPlus } from '@lucide/svelte';

	import GetReadyCard from './GetReadyCard.svelte';

	interface Props {
		user: CurrentUserDTO | null;
	}

	let { user }: Props = $props();

	const pwa = getPwaService();

	interface ReadyCard {
		key: string;
		title: string;
		description: string;
		icon: Component;
		actionLabel?: string;
		href?: Pathname;
		onclick?: () => void;
	}

	// Show the install card while the library reports it's available on this platform.
	let showPwa = $derived(pwa.canInstall);

	// Built in priority order so the first card is always the user's single most
	// important next step (account → ticket → schedule); the PWA nudge trails last.
	let cards = $derived.by<ReadyCard[]>(() => {
		const list: ReadyCard[] = [];

		if (!user) {
			list.push({
				key: 'account',
				title: 'Создать аккаунт',
				description: 'Нужен для голосования и подписки на выступления программы.',
				icon: UserPlus,
				actionLabel: 'Создать',
				href: '/login'
			});
		}

		if (user && !user.ticket) {
			list.push({
				key: 'ticket',
				title: 'Привязать билет',
				description: 'Открывает доступ к голосованию в конкурсных номинациях.',
				icon: Ticket,
				actionLabel: 'Привязать',
				href: '/profile'
			});
		}

		if (user) {
			list.push({
				key: 'schedule',
				title: 'Посмотреть программу',
				description: 'Подпишись на номера, чтобы не пропустить интересные выступления.',
				icon: Calendar,
				actionLabel: 'Смотреть',
				href: '/schedule'
			});

			list.push({
				key: 'notifications',
				title: 'Настроить уведомления',
				description: 'Получай напоминания о начале выступлений и изменениях в программе.',
				icon: Bell,
				actionLabel: 'Настроить',
				href: '/profile'
			});
		}

		if (showPwa) {
			list.push({
				key: 'pwa',
				title: 'Установить приложение',
				description: 'Быстрый доступ с главного экрана и пуш-уведомления.',
				icon: Download,
				actionLabel: 'Установить',
				// Open the install dialog directly; the library handles per-platform UX.
				onclick: () => pwa.showInstallDialog()
			});
		}

		return list;
	});

	// Lead with the top step as a prominent card; the rest fill a compact grid.
	let featured = $derived(cards[0]);
	let rest = $derived(cards.slice(1));
</script>

{#if featured}
	<section aria-labelledby="get-ready-heading" class="flex flex-col gap-3">
		<div class="flex max-w-3xl flex-col gap-1">
			<h2 id="get-ready-heading" class="text-lg font-semibold text-foreground">
				Подготовься к фестивалю
			</h2>
			<p class="text-sm leading-relaxed text-muted-foreground">
				Несколько шагов, чтобы получить максимум от приложения на мероприятии.
			</p>
		</div>

		<div class="flex flex-col gap-3">
			<GetReadyCard
				featured
				title={featured.title}
				description={featured.description}
				icon={featured.icon}
				actionLabel={featured.actionLabel}
				href={featured.href}
				onclick={featured.onclick}
			/>

			{#if rest.length > 0}
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each rest as card (card.key)}
						<GetReadyCard
							title={card.title}
							description={card.description}
							icon={card.icon}
							actionLabel={card.actionLabel}
							href={card.href}
							onclick={card.onclick}
						/>
					{/each}
				</div>
			{/if}
		</div>
	</section>
{/if}
