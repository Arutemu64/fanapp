<script lang="ts">
	import { resolve } from '$app/paths';
	import {
		Bell,
		ChevronRight,
		Download,
		Heart,
		MessageSquare,
		Palette,
		Ticket,
		UserRound,
		Wrench
	} from '@lucide/svelte';
	import { onMount } from 'svelte';
	import IconFastapi from '~icons/simple-icons/fastapi';
	import IconSvelte from '~icons/simple-icons/svelte';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import * as Avatar from '#lib/components/ui/avatar/index.js';
	import * as Item from '#lib/components/ui/item/index.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { reachability } from '#lib/services/reachability.js';
	import { LOGIN_NEXT_PARAM } from '#lib/utils/auth.js';
	import { isOrg } from '#lib/utils/permissions.js';
	import { type DevicePushState, getDevicePushState } from '#lib/utils/pushSubscription.js';
	import { getAvatarInitials, getRoleLabel } from '#lib/utils/users.js';

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
	let showStaleNotice = $derived(Boolean(user) && !reachability.current);

	// Return here after logging in: the guest opened the Profile tab, so that is
	// where they expect to land.
	const loginHref = `${resolve('login')}?${LOGIN_NEXT_PARAM}=${encodeURIComponent('/profile')}`;

	// Both baked in at build time (vite.config.ts `define`). The release number is
	// what an attendee can read out in a bug report ("у меня всё сломалось"); the
	// short SHA pins the exact bundle, since every build between two releases
	// carries the same number. A build without a release number (on the host,
	// outside Docker) hides the line rather than showing a blank one.
	const appVersion = __APP_VERSION__;
	const buildId = __APP_BUILD__.slice(0, 7);
</script>

<svelte:head>
	<title>Профиль · ФАН ФАН</title>
</svelte:head>

<!-- min-h-full fills the (app) shell's content column, so on a page shorter than the
	screen mt-auto drops the footer to the bottom instead of leaving it mid-screen. -->
<div class="flex min-h-full flex-col">
	<!-- Capped like a settings column: on a desktop the rows would otherwise stretch the
	     full content width and push each value and chevron far from its label. Centred,
	     because the shell centres its content column and a narrower block hugging that
	     column's left edge reads as lopsided. -->
	<div class="mx-auto flex w-full max-w-2xl flex-col gap-4 sm:gap-5">
		{#if showStaleNotice}
			<StaleDataNotice
				message="Нет связи. Показан сохранённый профиль — обновится при подключении."
			/>
		{/if}

		{#if user}
			<MenuGroup>
				<Item.Root class="rounded-none">
					{#snippet child({ props })}
						<a href={resolve('profile/account')} {...props}>
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
				<MenuLink href="profile/ticket" label="Билет" icon={Ticket} value={ticketStatus} />
				<MenuLink
					href="profile/notifications"
					label="Уведомления"
					icon={Bell}
					value={notificationsValue}
				/>
			</MenuGroup>

			<MenuGroup>
				<MenuLink href="feedback" label="Обратная связь" icon={MessageSquare} />
				{#if showTools}
					<MenuLink href="tools" label="Инструменты" icon={Wrench} />
				{/if}
			</MenuGroup>
		{:else}
			<!-- Takes the account row's slot and shape, so logging in fills the row in
			     rather than swapping the screen's layout. -->
			<MenuGroup>
				<Item.Root class="rounded-none">
					{#snippet child({ props })}
						<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- loginHref is resolve('/login') plus a query string, which the rule can't follow through a variable. -->
						<a href={loginHref} {...props}>
							<Item.Media>
								<Avatar.Root class="size-12">
									<Avatar.Fallback class="bg-primary/10 text-primary-700 dark:text-primary">
										<UserRound class="size-6" aria-hidden="true" />
									</Avatar.Fallback>
								</Avatar.Root>
							</Item.Media>
							<Item.Content class="min-w-0">
								<Item.Title class="text-base">Войти</Item.Title>
								<Item.Description>
									Голосование, подписки на выступления и уведомления
								</Item.Description>
							</Item.Content>
							<Item.Actions>
								<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
							</Item.Actions>
						</a>
					{/snippet}
				</Item.Root>
			</MenuGroup>
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
								<Item.Description
									>Быстрый запуск с главного экрана и пуш-уведомления</Item.Description
								>
							</Item.Content>
						</button>
					{/snippet}
				</Item.Root>
			{/if}
			<!-- An icon like every other hub row: the install row above shares this card,
			     and a list that gives icons to only some rows reads as two layouts. -->
			<Item.Root class="rounded-none">
				<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
					<Palette class="size-5" aria-hidden="true" />
				</Item.Media>
				<Item.Content>
					<Item.Title class="text-base">Тема</Item.Title>
				</Item.Content>
				<Item.Footer>
					<ThemeToggle />
				</Item.Footer>
			</Item.Root>
		</MenuGroup>

		{#if user}
			<LogoutButton />
		{/if}
	</div>

	<footer class="mx-auto mt-auto max-w-2xl pt-6 text-center text-xs text-muted-foreground">
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
		{#if appVersion}
			<p class="mt-0.5">
				Версия {appVersion}
				{#if buildId}· {buildId}{/if}
			</p>
		{/if}
	</footer>
</div>
