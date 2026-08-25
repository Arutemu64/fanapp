<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { Component } from 'svelte';

	import { page } from '$app/state';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import {
		canGenerateTickets,
		canImportSchedule,
		canManageSettings,
		canManageVoting,
		canReadFeedback,
		canReadUsers,
		canRunSync,
		canSendNotifications
	} from '$lib/utils/permissions';
	import {
		AdjustmentsHorizontalOutline,
		AnnotationOutline,
		AwardOutline,
		BullhornOutline,
		FileImportOutline,
		RefreshOutline,
		TicketOutline,
		UsersGroupOutline
	} from 'flowbite-svelte-icons';

	import ToolCard from './components/ToolCard.svelte';

	let user: CurrentUserDTO | null = $derived(page.data.user);

	interface Tool {
		key: string;
		title: string;
		description: string;
		icon: Component;
		href: Pathname;
		/** Whether this org holds the permission this tool needs. */
		canAccess: boolean;
	}

	// Locked tools stay in the grid so an org sees the whole toolbox and knows what
	// they'd need granted, rather than the section silently shrinking per account.
	let tools = $derived<Tool[]>([
		{
			key: 'settings',
			title: 'Настройки фестиваля',
			description: 'Даты фестиваля и тайминги программы.',
			icon: AdjustmentsHorizontalOutline,
			href: '/tools/settings',
			canAccess: canManageSettings(user)
		},
		{
			key: 'voting',
			title: 'Голосование',
			description: 'Включай голосование, следи за лидерами и разыгрывай приз.',
			icon: AwardOutline,
			href: '/tools/voting',
			canAccess: canManageVoting(user)
		},
		{
			key: 'import_schedule',
			title: 'Импорт программы',
			description: 'Загрузи программу из Excel-файла.',
			icon: FileImportOutline,
			href: '/tools/import_schedule',
			canAccess: canImportSchedule(user)
		},
		{
			key: 'broadcast',
			title: 'Рассылка уведомлений',
			description: 'Массовые уведомления для выбранных категорий участников.',
			icon: BullhornOutline,
			href: '/tools/broadcast',
			canAccess: canSendNotifications(user)
		},
		{
			key: 'generate_tickets',
			title: 'Генерация билетов',
			description: 'Новые билеты для выбранной роли — получатель привязывает по номеру.',
			icon: TicketOutline,
			href: '/tools/generate_tickets',
			canAccess: canGenerateTickets(user)
		},
		{
			key: 'sync',
			title: 'Синхронизация',
			description: 'Подтяни свежие данные вручную, не дожидаясь автообновления.',
			icon: RefreshOutline,
			href: '/tools/sync',
			canAccess: canRunSync(user)
		},
		{
			key: 'feedback',
			title: 'Отзывы',
			description: 'Что участники пишут о приложении — свежие отзывы сверху.',
			icon: AnnotationOutline,
			href: '/tools/feedback',
			canAccess: canReadFeedback(user)
		},
		{
			key: 'users',
			title: 'Пользователи',
			description: 'Список всех пользователей с поиском и карточкой каждого.',
			icon: UsersGroupOutline,
			href: '/tools/users',
			canAccess: canReadUsers(user)
		}
	]);
</script>

<SectionIntro
	description="Для работы организаторов фестиваля. Серые карточки — те, к которым у тебя пока нет доступа."
/>

<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
	{#each tools as tool (tool.key)}
		<ToolCard
			title={tool.title}
			description={tool.description}
			icon={tool.icon}
			href={tool.href}
			locked={!tool.canAccess}
		/>
	{/each}
</div>
