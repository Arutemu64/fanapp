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
	import SettingsSection from '#lib/components/SettingsSection.svelte';
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

	interface ToolGroup {
		key: string;
		title: string;
		tools: Tool[];
	}

	// Locked tools stay in the list so an org sees the whole toolbox and knows what
	// they'd need granted, rather than the section silently shrinking per account.
	// Two headed groups instead of one long list of eight, the /profile hub's shape.
	let groups = $derived<ToolGroup[]>([
		{
			key: 'festival',
			title: 'Фестиваль и программа',
			tools: [
				{
					key: 'settings',
					title: 'Настройки фестиваля',
					description: 'Даты фестиваля и тайминги программы.',
					icon: SlidersHorizontal,
					href: 'tools/settings',
					canAccess: canManageSettings(user)
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
					key: 'sync',
					title: 'Синхронизация',
					description: 'Подтяни свежие данные вручную, не дожидаясь автообновления.',
					icon: RotateCw,
					href: 'tools/sync',
					canAccess: canRunSync(user)
				},
				{
					key: 'voting',
					title: 'Голосование',
					description: 'Включай голосование, следи за лидерами и разыгрывай приз.',
					icon: Award,
					href: 'tools/voting',
					canAccess: canManageVoting(user)
				}
			]
		},
		{
			key: 'people',
			title: 'Участники',
			tools: [
				{
					key: 'broadcast',
					title: 'Рассылка уведомлений',
					description: 'Массовые уведомления для выбранных категорий участников.',
					icon: Megaphone,
					href: 'tools/broadcast',
					canAccess: canSendNotifications(user)
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
				},
				{
					key: 'generate-tickets',
					title: 'Генерация билетов',
					description: 'Новые билеты для выбранной роли — получатель привязывает по номеру.',
					icon: Ticket,
					href: 'tools/generate-tickets',
					canAccess: canGenerateTickets(user)
				}
			]
		}
	]);

	let hasLockedTools = $derived(
		groups.some((group) => group.tools.some((tool) => !tool.canAccess))
	);
	let intro = $derived(
		hasLockedTools
			? 'Для работы организаторов фестиваля. Инструменты с замком тебе пока недоступны.'
			: 'Для работы организаторов фестиваля.'
	);
</script>

<SectionIntro description={intro} />

<div class="flex flex-col gap-6">
	<!-- Shown to every org: the tools layout already gates this whole section to the
	     org role, so no per-tool permission scopes the live count. -->
	<OnlineNowCard />

	{#each groups as group (group.key)}
		<SettingsSection title={group.title}>
			<MenuGroup>
				{#each group.tools as tool (tool.key)}
					<ToolRow
						title={tool.title}
						description={tool.description}
						icon={tool.icon}
						href={tool.href}
						locked={!tool.canAccess}
					/>
				{/each}
			</MenuGroup>
		</SettingsSection>
	{/each}
</div>
