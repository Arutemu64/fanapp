<script lang="ts">
	import {
		PUBLIC_TELEGRAM_BOT_USERNAME,
		PUBLIC_VAPID_KEY,
		PUBLIC_VK_GROUP_ID
	} from '$app/env/public';
	import { resolve } from '$app/paths';
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { CurrentUserDto, UpdateUserSettingsInput } from '#lib/api/generated/index.js';
	import type { MessageTagProps } from '#lib/types/markup.js';

	import {
		createPushSubscriptionMutation,
		deletePushSubscriptionMutation,
		getCurrentUserQueryKey,
		sendTestNotificationMutation,
		updateCurrentUserSettingsMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import {
		checkPushSubscription,
		enableTelegramNotifications,
		enableVkNotifications
	} from '#lib/api/generated/index.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SwitchRow from '#lib/components/SwitchRow.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { trackEvent } from '#lib/services/analytics.js';
	import { PushDevice, type PushToggleOutcome } from '#lib/services/pushDevice.svelte.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';
	import { getSocialProviderLabel } from '#lib/utils/users.js';

	import MessengerNotificationsDialog from './MessengerNotificationsDialog.svelte';
	import SettingsSection from './SettingsSection.svelte';

	interface Props {
		user: CurrentUserDto;
	}

	let { user }: Props = $props();
	const queryClient = useQueryClient();

	function refreshUser() {
		return queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
	}

	const pushSubscribeMutation = createMutation(() => ({
		...createPushSubscriptionMutation(),
		onSuccess: () => {
			trackEvent('push-enable');
			return refreshUser();
		}
	}));
	const pushUnsubscribeMutation = createMutation(() => ({
		...deletePushSubscriptionMutation(),
		onSuccess: () => {
			trackEvent('push-disable');
			return refreshUser();
		}
	}));
	const settingsMutation = createMutation(() => ({
		...updateCurrentUserSettingsMutation(),
		onSuccess: refreshUser
	}));
	const testMutation = createMutation(() => sendTestNotificationMutation());

	const offlineGate = offlineWriteGate();

	const toastService = getToastService();
	let hasVkAccount = $derived(
		user.social_identities.some((socialIdentity) => socialIdentity.provider === 'vk')
	);
	let receiveVk = $derived(hasVkAccount && user.settings.receive_vk_notifications);
	let hasTelegramAccount = $derived(
		user.social_identities.some((socialIdentity) => socialIdentity.provider === 'telegram')
	);
	let receiveTelegram = $derived(
		hasTelegramAccount && user.settings.receive_telegram_notifications
	);
	let showTelegramModal = $state(false);
	let vkDescription = $derived(
		hasVkAccount ? m.vk_notifications_on_description() : m.vk_notifications_connect_first()
	);
	const pwa = getPwaService();
	let showVkModal = $state(false);
	const vkGroupUrl = PUBLIC_VK_GROUP_ID ? `https://vk.ru/write-${PUBLIC_VK_GROUP_ID}` : null;
	const telegramBotUrl = PUBLIC_TELEGRAM_BOT_USERNAME
		? `https://t.me/${PUBLIC_TELEGRAM_BOT_USERNAME}`
		: null;

	let blockedHint = $derived.by(() => {
		if (!pwa.isInstalled) {
			return m.push_blocked_browser();
		}
		if (pwa.isApplePlatform) {
			return m.push_off_device();
		}
		return m.push_off_phone();
	});

	const pushDevice = new PushDevice({
		vapidKey: PUBLIC_VAPID_KEY,
		backend: {
			async isRegistered(endpoint) {
				const { data } = await checkPushSubscription({ body: { endpoint } });
				return data?.subscribed ?? false;
			},
			async register(registration) {
				await pushSubscribeMutation.mutateAsync({ body: registration });
			},
			async unregister(endpoint) {
				await pushUnsubscribeMutation.mutateAsync({ body: { endpoint } });
			}
		}
	});

	onMount(() => {
		void pushDevice.refresh();
	});

	const toggleFailureCopy: Record<Exclude<PushToggleOutcome, 'enabled' | 'disabled'>, string> = {
		unsupported: m.push_status_unsupported(),
		unavailable: m.push_status_unavailable(),
		blocked: m.push_status_blocked(),
		'not-granted': m.push_status_not_granted(),
		incomplete: m.push_error_incomplete(),
		rejected: m.push_error_rejected(),
		failed: m.push_error_failed(),
		'disable-failed': m.push_error_disable_failed()
	};

	async function toggleSubscription() {
		if (pushDevice.state !== 'on' && pwa.pushRequiresInstall && !pwa.isInstalled) {
			pwa.showInstallDialog();
			return;
		}

		const outcome = await pushDevice.toggle();
		if (outcome !== 'enabled' && outcome !== 'disabled') {
			toastService.add(toggleFailureCopy[outcome], 'error');
		}
	}

	function updateSettings(nextSettings: Partial<UpdateUserSettingsInput>, rollback: () => void) {
		settingsMutation.mutate(
			{ body: nextSettings },
			{
				onError: () => {
					toastService.add(m.push_settings_update_failed(), 'error');
					rollback();
				}
			}
		);
	}

	// Switching a messenger on goes through its dialog: the server enables it only once it can write.
	function toggleReceiveTelegram(checked: boolean) {
		if (checked) {
			showTelegramModal = true;
			return;
		}
		receiveTelegram = false;
		updateSettings({ receive_telegram_notifications: false }, () => {
			receiveTelegram = hasTelegramAccount && user.settings.receive_telegram_notifications;
		});
	}

	function toggleReceiveVk(checked: boolean) {
		if (checked) {
			showVkModal = true;
			return;
		}
		receiveVk = false;
		updateSettings({ receive_vk_notifications: false }, () => {
			receiveVk = hasVkAccount && user.settings.receive_vk_notifications;
		});
	}

	function sendTestNotification() {
		testMutation.mutate(
			{},
			{
				onSuccess: () => {
					toastService.add(m.push_test_sent(), 'success');
				},
				onError: (error) => toastService.error(error, m.push_test_failed())
			}
		);
	}
</script>

<div class="flex flex-col gap-6">
	<p class="text-sm leading-5 text-muted-foreground">
		{m.push_settings_intro()}
	</p>

	<SettingsSection title={m.push_channels_title()}>
		<MenuGroup class="divide-y divide-border">
			<SwitchRow
				id="push-this-device"
				title={m.push_this_device_title()}
				description={m.push_this_device_description()}
				checked={pushDevice.state === 'on'}
				disabled={pushDevice.isBusy || pushDevice.state === 'unsupported'}
				blocked={offlineGate.blocked}
				onCheckedChange={offlineGate.guard(() => {
					void toggleSubscription();
				})}
			>
				{#if pushDevice.state === 'unsupported'}
					<p class="mt-2 text-sm leading-relaxed text-muted-foreground">
						{m.push_open_in_browser()}
					</p>
				{:else if pushDevice.state === 'blocked'}
					<p class="mt-2 text-sm leading-relaxed text-destructive">{blockedHint}</p>
				{/if}
			</SwitchRow>

			{#if hasTelegramAccount}
				<SwitchRow
					id="telegram-notifications"
					title={getSocialProviderLabel('telegram')}
					description={m.telegram_notifications_on_description()}
					checked={receiveTelegram}
					disabled={settingsMutation.isPending}
					blocked={offlineGate.blocked}
					onCheckedChange={offlineGate.guard(toggleReceiveTelegram)}
				/>
			{/if}

			<SwitchRow
				id="vk-notifications"
				title={m.social_vk()}
				description={vkDescription}
				checked={receiveVk}
				disabled={settingsMutation.isPending || !hasVkAccount}
				blocked={offlineGate.blocked}
				onCheckedChange={offlineGate.guard(toggleReceiveVk)}
			>
				<div class="flex flex-wrap gap-x-4">
					{#if !hasVkAccount}
						<a
							href={resolve('profile/account')}
							class="inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline"
						>
							{m.vk_connect()}
						</a>
					{/if}
					<button
						type="button"
						class="inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline"
						onclick={() => (showVkModal = true)}
					>
						{m.vk_how_it_works()}
					</button>
				</div>
			</SwitchRow>
		</MenuGroup>
	</SettingsSection>

	<div>
		<p class="mb-3 text-sm leading-relaxed text-muted-foreground">
			{m.push_test_hint()}
		</p>
		<Button
			variant="outline"
			class="w-full sm:w-auto"
			disabled={testMutation.isPending}
			aria-disabled={offlineGate.blocked}
			onclick={offlineGate.guard(sendTestNotification)}
		>
			{#if testMutation.isPending}
				<Spinner data-icon="inline-start" />
				{m.common_sending()}
			{:else}
				{m.push_test_action()}
			{/if}
		</Button>
	</div>
</div>

<MessengerNotificationsDialog
	bind:open={showVkModal}
	title={m.vk_modal_title()}
	intro={m.vk_modal_intro()}
	chatUrl={vkGroupUrl}
	chatLabel={m.vk_modal_open_community()}
	canCheck={hasVkAccount}
	enable={() => enableVkNotifications({ throwOnError: true })}
	enabledMessage={m.vk_enabled()}
>
	{#snippet steps()}
		{#if !hasVkAccount}
			<li>
				<ParaglideMessage message={m.vk_modal_step_connect}>
					{#snippet link({ children }: MessageTagProps)}
						<a href={resolve('profile/account')} class="font-medium text-primary hover:underline"
							>{@render children?.()}</a
						>
					{/snippet}
				</ParaglideMessage>
			</li>
		{/if}
		<li>{m.vk_modal_step_allow()}</li>
		{#if hasVkAccount}
			<li>{m.vk_modal_step_check()}</li>
		{/if}
	{/snippet}
</MessengerNotificationsDialog>

<MessengerNotificationsDialog
	bind:open={showTelegramModal}
	title={m.telegram_modal_title()}
	intro={m.telegram_modal_intro()}
	chatUrl={telegramBotUrl}
	chatLabel={m.telegram_modal_open_bot()}
	canCheck={hasTelegramAccount}
	enable={() => enableTelegramNotifications({ throwOnError: true })}
	enabledMessage={m.telegram_enabled()}
>
	{#snippet steps()}
		<li>{m.telegram_modal_step_unblock()}</li>
		<li>{m.telegram_modal_step_check()}</li>
	{/snippet}
</MessengerNotificationsDialog>
