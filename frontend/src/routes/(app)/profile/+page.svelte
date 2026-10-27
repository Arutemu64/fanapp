<script lang="ts">
	import { resolve } from '$app/paths';
	import Bell from '@lucide/svelte/icons/bell';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Download from '@lucide/svelte/icons/download';
	import Heart from '@lucide/svelte/icons/heart';
	import MessageSquare from '@lucide/svelte/icons/message-square';
	import Palette from '@lucide/svelte/icons/palette';
	import RotateCw from '@lucide/svelte/icons/rotate-cw';
	import Ticket from '@lucide/svelte/icons/ticket';
	import Trophy from '@lucide/svelte/icons/trophy';
	import UserRound from '@lucide/svelte/icons/user-round';
	import Wrench from '@lucide/svelte/icons/wrench';
	import { createQuery } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';
	import IconFastapi from '~icons/simple-icons/fastapi';
	import IconSvelte from '~icons/simple-icons/svelte';

	import {
		getPublicConfigOptions,
		getQuestOptions
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import * as Avatar from '#lib/components/ui/avatar/index.js';
	import * as Item from '#lib/components/ui/item/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import Username from '#lib/components/Username.svelte';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { toolsFor } from '#lib/data/tools.js';
	import { m } from '#lib/paraglide/messages.js';
	import { trackEvent } from '#lib/services/analytics.js';
	import { getAppUpdateService } from '#lib/services/appUpdate.svelte.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { type DevicePushState, getDevicePushState } from '#lib/services/pushDevice.svelte.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { LOGIN_NEXT_PARAM } from '#lib/utils/auth.js';
	import { isStaff } from '#lib/utils/permissions.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	import DiagnosticsDialog from './components/DiagnosticsDialog.svelte';
	import LogoutButton from './components/LogoutButton.svelte';
	import ThemeToggle from './components/ThemeToggle.svelte';
	import { notificationsStatus } from './notificationsStatus';

	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? null);
	let ticketStatus = $derived(
		user?.ticket ? m.ticket_status_linked() : m.ticket_status_not_linked()
	);

	let devicePush = $state<DevicePushState>('unknown');
	let notificationsValue = $derived(user ? notificationsStatus(devicePush, user) : undefined);

	onMount(() => {
		void getDevicePushState().then((state) => {
			devicePush = state;
		});
	});

	const configQuery = createQuery(() => getPublicConfigOptions());
	let questEnabled = $derived((configQuery.data ?? FALLBACK_CONFIG).quest_enabled);
	let showTools = $derived(
		isStaff(user) && toolsFor(user, configQuery.data ?? FALLBACK_CONFIG).length > 0
	);
	const questQuery = createQuery(() => ({
		...getQuestOptions(),
		enabled: questEnabled && user !== null
	}));
	let questValue = $derived.by(() => {
		const quest = questQuery.data;
		if (!quest) {
			return undefined;
		}
		return m.quest_points({ count: quest.points });
	});

	const pwa = getPwaService();
	const appUpdate = getAppUpdateService();

	const loginHref = resolve(`login?${LOGIN_NEXT_PARAM}=${encodeURIComponent('/profile')}`);

	const appVersion = __APP_VERSION__;
	const buildId = __APP_BUILD__.slice(0, 7);

	const DIAGNOSTICS_TAPS = 5;
	const DIAGNOSTICS_TAP_WINDOW_MS = 2000;
	let versionTaps: number[] = [];
	let diagnosticsOpen = $state(false);

	function handleVersionTap() {
		const now = Date.now();
		versionTaps = [...versionTaps, now].filter((at) => now - at < DIAGNOSTICS_TAP_WINDOW_MS);
		if (versionTaps.length >= DIAGNOSTICS_TAPS) {
			versionTaps = [];
			diagnosticsOpen = true;
		}
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_profile() })}</title>
</svelte:head>

<div data-fill-column class="flex grow flex-col">
	<div class="mx-auto flex w-full max-w-2xl flex-col gap-4 sm:gap-5">
		{#if appUpdate.available}
			<MenuGroup>
				<MenuRow
					onclick={() => {
						trackEvent('app-update');
						appUpdate.apply();
					}}
					label={m.profile_update_app()}
					description={m.profile_update_app_description()}
					icon={RotateCw}
					tone="primary"
				/>
			</MenuGroup>
		{/if}

		{#if user}
			<MenuGroup>
				<Item.Root class="rounded-none">
					{#snippet child({ props })}
						<a href={resolve('profile/account')} {...props}>
							<Item.Media>
								<UserAvatar seed={user.avatar_seed} class="size-12" />
							</Item.Media>
							<Item.Content class="min-w-0">
								<Item.Title class="line-clamp-none max-w-full text-base">
									<Username username={user.username} class="min-w-0" />
								</Item.Title>
								<Item.Description
									>{m.profile_menu_account_description({
										role: getRoleLabel(user.role)
									})}</Item.Description
								>
							</Item.Content>
							<Item.Actions>
								<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
							</Item.Actions>
						</a>
					{/snippet}
				</Item.Root>
			</MenuGroup>

			{#if questEnabled}
				<MenuGroup>
					<MenuRow href="profile/quest" label={m.quest_title()} icon={Trophy} value={questValue} />
				</MenuGroup>
			{/if}

			<MenuGroup>
				<MenuRow
					href="profile/ticket"
					label={m.ticket_title()}
					icon={Ticket}
					value={ticketStatus}
				/>
				<MenuRow
					href="profile/notifications"
					label={m.notifications_title()}
					icon={Bell}
					value={notificationsValue}
				/>
			</MenuGroup>

			<MenuGroup>
				<MenuRow href="feedback" label={m.feedback_title()} icon={MessageSquare} />
				{#if showTools}
					<MenuRow href="tools" label={m.tools_title()} icon={Wrench} />
				{/if}
			</MenuGroup>
		{:else}
			<MenuGroup>
				<Item.Root class="rounded-none">
					{#snippet child({ props })}
						<a href={loginHref} {...props}>
							<Item.Media>
								<Avatar.Root class="size-12">
									<Avatar.Fallback class="bg-primary/10 text-primary-700 dark:text-primary">
										<UserRound class="size-6" aria-hidden="true" />
									</Avatar.Fallback>
								</Avatar.Root>
							</Item.Media>
							<Item.Content class="min-w-0">
								<Item.Title class="text-base">{m.common_login()}</Item.Title>
								<Item.Description>
									{m.profile_login_description()}
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
				<MenuRow
					onclick={() => pwa.showInstallDialog()}
					label={m.install_title()}
					description={m.profile_install_description()}
					icon={Download}
				/>
			{/if}
			<Item.Root class="rounded-none">
				<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
					<Palette class="size-5" aria-hidden="true" />
				</Item.Media>
				<Item.Content>
					<Item.Title class="text-base">{m.profile_theme()}</Item.Title>
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
			{m.footer_powered_by()}
			<IconSvelte class="inline size-3.5 text-[#FF3E00]" />
			{m.footer_svelte_and()}
			<IconFastapi class="inline size-3.5 text-[#009688]" />
			FastAPI
		</p>
		<p class="flex items-center justify-center gap-1">
			{m.footer_with_love()}
			<a
				href="https://arutemu64.com/"
				target="_blank"
				rel="noopener noreferrer"
				class="inline-flex min-h-6 items-center underline hover:text-foreground"
			>
				Arutemu64
			</a>
			<Heart class="inline size-3.5 text-red-400" />
		</p>
		{#if appVersion}
			<button
				type="button"
				class="inline-flex min-h-6 cursor-default items-center select-none"
				onclick={handleVersionTap}
			>
				{m.footer_version({ version: appVersion })}
				{#if buildId}· {buildId}{/if}
			</button>
		{/if}
	</footer>
</div>

<DiagnosticsDialog bind:open={diagnosticsOpen} {user} version={appVersion} build={__APP_BUILD__} />
