<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import { page } from '$app/state';
	import {
		Award,
		FileUp,
		Megaphone,
		MessageSquare,
		RotateCw,
		SlidersHorizontal,
		Ticket,
		Users
	} from '@lucide/svelte';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import {
		canGenerateTickets,
		canImportSchedule,
		canManageSettings,
		canManageVoting,
		canReadFeedback,
		canReadUsers,
		canRunSync,
		canSendNotifications
	} from '#lib/utils/permissions.js';

	import OnlineNowCard from './components/OnlineNowCard.svelte';
	import ToolRow from './components/ToolRow.svelte';

	let user: CurrentUserDto | null = $derived(page.data.user);

	interface Tool {
		key: string;
		title: string;
		description: string;
		icon: Component;
		href: Path;
		/** Whether this org holds the permission this tool needs. */
		canAccess: boolean;
	}

	// Locked tools stay in the list so an org sees the whole toolbox and knows what
	// they'd need granted, rather than the section silently shrinking per account.
	let tools = $derived<Tool[]>([
		{
			key: 'settings',
			title: 'Настройки фестиваля',
			description: 'Даты фестиваля и тайминги программы.',
			icon: SlidersHorizontal,
			href: 'tools/settings',
			canAccess: canManageSettings(user)
		},
		{
			key: 'voting',
			title: 'Голосование',
			description: 'Включай голосование, следи за лидерами и разыгрывай приз.',
			icon: Award,
			href: 'tools/voting',
			canAccess: canManageVoting(user)
		},
		{
			key: 'import-schedule',
			title: 'Импорт программы',
			description: 'Загрузи программу из Excel-файла.',
			icon: FileUp,
			href: 'tools/import-schedule',
			canAccess: canImportSchedule(user)
		},
		{
			key: 'broadcast',
			title: 'Рассылка уведомлений',
			description: 'Массовые уведомления для выбранных категорий участников.',
			icon: Megaphone,
			href: 'tools/broadcast',
			canAccess: canSendNotifications(user)
		},
		{
			key: 'generate-tickets',
			title: 'Генерация билетов',
			description: 'Новые билеты для выбранной роли — получатель привязывает по номеру.',
			icon: Ticket,
			href: 'tools/generate-tickets',
			canAccess: canGenerateTickets(user)
		},
		{
			key: 'sync',
			title: 'Синхронизация',
			description: 'Подтяни свежие данные вручную, не дожидаясь автообновления.',
			icon: RotateCw,
			href: 'tools/sync',
			canAccess: canRunSync(user)
		},
		{
			key: 'feedback',
			title: 'Отзывы',
			description: 'Что участники пишут о приложении — свежие отзывы сверху.',
			icon: MessageSquare,
			href: 'tools/feedback',
			canAccess: canReadFeedback(user)
		},
		{
			key: 'users',
			title: 'Пользователи',
			description: 'Список всех пользователей с поиском и карточкой каждого.',
			icon: Users,
			href: 'tools/users',
			canAccess: canReadUsers(user)
		}
	]);
</script>

<!-- Capped and centred like the /profile hub this menu continues. -->
<div class="mx-auto max-w-2xl">
	<SectionIntro
		description="Для работы организаторов фестиваля. Инструменты с замком тебе пока недоступны."
	/>

	<!-- Shown to every org: the tools layout already gates this whole section to the
	     org role, so no per-tool permission scopes the live count. -->
	<div class="mb-4">
		<OnlineNowCard />
	</div>

	<MenuGroup>
		{#each tools as tool (tool.key)}
			<ToolRow
				title={tool.title}
				description={tool.description}
				icon={tool.icon}
				href={tool.href}
				locked={!tool.canAccess}
			/>
		{/each}
	</MenuGroup>
</div>
