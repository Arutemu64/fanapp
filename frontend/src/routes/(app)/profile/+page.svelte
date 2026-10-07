<script lang="ts">
	import { resolve } from '$app/paths';
	import { PUBLIC_APP_VERSION } from '$env/static/public';
	import MenuGroup from '$lib/components/MenuGroup.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import * as Avatar from '$lib/components/ui/avatar';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Item from '$lib/components/ui/item';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import { LOGIN_NEXT_PARAM } from '$lib/utils/auth';
	import { isOrg } from '$lib/utils/permissions';
	import { type DevicePushState, getDevicePushState } from '$lib/utils/pushSubscription';
	import { getAvatarInitials, getRoleLabel } from '$lib/utils/users';
	import {
		Bell,
		ChevronRight,
		Download,
		Heart,
		LogIn,
		MessageSquare,
		Ticket,
		Wrench
	} from '@lucide/svelte';
	import { onMount } from 'svelte';
	import IconFastapi from '~icons/simple-icons/fastapi';
	import IconSvelte from '~icons/simple-icons/svelte';

	import type { PageProps } from './$types';

	import LogoutButton from './components/LogoutButton.svelte';
	import MenuLink from './components/MenuLink.svelte';
	import ThemeToggle from './components/ThemeToggle.svelte';
	import { notificationsStatus } from './notificationsStatus';

	let { data }: PageProps = $props();
	let user = $derived(data.user);
	let avatarInitials = $derived(getAvatarInitials(user?.username));
	let ticketStatus = $derived(user?.ticket ? 'Привязан' : 'Не привязан');

	// The row's "current value", like a settings screen's: whether any channel
	// reaches this user (see notificationsStatus). Device push is read from the
	// browser after mount; until then the social channels speak alone.
	let devicePush = $state<DevicePushState>('unknown');
	let notificationsValue = $derived(user ? notificationsStatus(devicePush, user) : undefined);

	onMount(() => {
		void getDevicePushState().then((state) => {
			devicePush = state;
		});
	});

	// "Инструменты" is the organiser toolbox: a single link to the /tools dashboard
	// rather than a row per tool, so the hub stays short as the tool list grows. It
	// is org-only for now; per-tool permission gating lives on the dashboard, where
	// locked tools show as a discovery cue.
	let showTools = $derived(isOrg(user));

	const pwa = getPwaService();

	// The account row and ticket status render from the layout-cached user, so
	// offline they may be out of date; say so, as the settings pages behind it do.
	const offline = getOfflineService();
	let showStaleNotice = $derived(Boolean(user) && !offline.isOnline);

	// Return here after logging in: the guest opened the Profile tab, so that is
	// where they expect to land.
	const loginHref = `${resolve('/login')}?${LOGIN_NEXT_PARAM}=${encodeURIComponent('/profile')}`;

	// Commit SHA baked in at build time, shortened for display. Empty for a local
	// build from source — then the line is hidden rather than showing a blank id.
	// It exists so a bug report ("у меня всё сломалось") names an exact bundle.
	const buildId = PUBLIC_APP_VERSION.slice(0, 7);
</script>

<svelte:head>
	<title>Профиль · ФАН ФАН</title>
</svelte:head>

<!-- Capped like a settings column: on a desktop the rows would otherwise stretch the
     full content width and push each value and chevron far from its label. Centred,
     because the shell centres its content column and a narrower block hugging that
     column's left edge reads as lopsided. -->
<div class="mx-auto flex max-w-2xl flex-col gap-4 sm:gap-5">
	{#if showStaleNotice}
		<StaleDataNotice
			message="Нет связи. Показан сохранённый профиль — обновится при подключении."
		/>
	{/if}

	{#if user}
		<MenuGroup>
			<Item.Root class="rounded-none">
				{#snippet child({ props })}
					<a href={resolve('/profile/account')} {...props}>
						<Item.Media>
							<Avatar.Root class="size-12 text-base font-bold">
								<Avatar.Fallback class="bg-primary/10 text-primary-700 dark:text-primary">
									{avatarInitials}
								</Avatar.Fallback>
							</Avatar.Root>
						</Item.Media>
						<Item.Content class="min-w-0">
							<Item.Title class="max-w-full text-base">
								<span class="truncate">@{user.username}</span>
							</Item.Title>
							<Item.Description>{getRoleLabel(user.role)} · аккаунт и вход</Item.Description>
						</Item.Content>
						<Item.Actions>
							<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
						</Item.Actions>
					</a>
				{/snippet}
			</Item.Root>
		</MenuGroup>

		<MenuGroup>
			<MenuLink href="/profile/ticket" label="Билет" icon={Ticket} value={ticketStatus} />
			<MenuLink
				href="/profile/notifications"
				label="Уведомления"
				icon={Bell}
				value={notificationsValue}
			/>
		</MenuGroup>

		<MenuGroup>
			<MenuLink href="/feedback" label="Обратная связь" icon={MessageSquare} />
			{#if showTools}
				<MenuLink href="/tools" label="Инструменты" icon={Wrench} />
			{/if}
		</MenuGroup>
	{:else}
		<Card.Root class="w-full max-w-none rounded-2xl">
			<div class="flex flex-col gap-4 px-5 sm:px-6">
				<div class="flex flex-col gap-1">
					<h2 class="text-lg font-bold text-foreground">Войди в аккаунт</h2>
					<p class="text-sm leading-5 text-muted-foreground">
						С аккаунтом можно голосовать, подписываться на выступления и получать уведомления.
					</p>
				</div>
				<Button href={loginHref} size="lg" class="w-full sm:w-auto">
					<LogIn data-icon="inline-start" />
					Войти
				</Button>
			</div>
		</Card.Root>
	{/if}

	<MenuGroup>
		{#if pwa.canInstall}
			<!-- Opens the @khmyznikov/pwa-install dialog, which renders its own
			     platform-specific instructions (Chromium prompt, iOS "На экран Домой").
			     hover:bg-muted by hand: Item only highlights rows rendered as <a>. -->
			<Item.Root class="rounded-none hover:bg-muted">
				{#snippet child({ props })}
					<button type="button" {...props} onclick={() => pwa.showInstallDialog()}>
						<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
							<Download class="size-5" aria-hidden="true" />
						</Item.Media>
						<Item.Content>
							<Item.Title class="text-base">Установить приложение</Item.Title>
							<Item.Description>Быстрый запуск с главного экрана и пуш-уведомления</Item.Description
							>
						</Item.Content>
					</button>
				{/snippet}
			</Item.Root>
		{/if}
		<div class="flex flex-col gap-3 px-4 py-3.5">
			<span class="text-base font-medium">Тема</span>
			<ThemeToggle />
		</div>
	</MenuGroup>

	{#if user}
		<LogoutButton />
	{/if}
</div>

<footer class="mx-auto mt-6 max-w-2xl text-center text-xs text-muted-foreground">
	<p class="flex items-center justify-center gap-1">
		Работает на
		<IconSvelte class="inline size-3.5 text-[#FF3E00]" />
		Svelte и
		<IconFastapi class="inline size-3.5 text-[#009688]" />
		FastAPI
	</p>
	<p class="mt-0.5 flex items-center justify-center gap-1">
		С любовью,
		<a
			href="https://arutemu64.com/"
			target="_blank"
			rel="noopener noreferrer"
			class="underline hover:text-foreground"
		>
			Arutemu64
		</a>
		<Heart class="inline size-3.5 text-red-400" />
	</p>
	{#if buildId}
		<p class="mt-0.5">Сборка {buildId}</p>
	{/if}
</footer>
