<script lang="ts">
	import { PUBLIC_VAPID_KEY, PUBLIC_VK_GROUP_ID } from '$app/env/public';
	import { resolve } from '$app/paths';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { CurrentUserDto, UpdateUserSettingsInput } from '#lib/api/generated/index.js';

	import {
		createPushSubscriptionMutation,
		deletePushSubscriptionMutation,
		getCurrentUserQueryKey,
		sendTestNotificationMutation,
		updateCurrentUserSettingsMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { checkPushSubscription } from '#lib/api/generated/index.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SwitchRow from '#lib/components/SwitchRow.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { PushDevice, type PushToggleOutcome } from '#lib/services/pushDevice.svelte.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import SettingsSection from './SettingsSection.svelte';
	import VkNotificationsModal from './VkNotificationsModal.svelte';

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
		onSuccess: refreshUser
	}));
	const pushUnsubscribeMutation = createMutation(() => ({
		...deletePushSubscriptionMutation(),
		onSuccess: refreshUser
	}));
	const settingsMutation = createMutation(() => ({
		...updateCurrentUserSettingsMutation(),
		onSuccess: refreshUser
	}));
	const testMutation = createMutation(() => sendTestNotificationMutation());

	// Every control here writes to the server (push subscribe/unsubscribe, settings
	// PATCH, test send) — online only. The current toggle states still render.
	const offlineGate = offlineWriteGate();

	const toastService = getToastService();
	let hasVkAccount = $derived(
		user.social_identities.some((socialIdentity) => socialIdentity.provider === 'vk')
	);
	// Writable derived: the toggle overrides it optimistically, and it snaps back
	// to the server copy whenever `user` refreshes (Svelte "Overriding derived values").
	let receiveVk = $derived(hasVkAccount && (user.settings.receive_vk_notifications ?? false));
	let vkDescription = $derived(
		hasVkAccount ? m.vk_notifications_on_description() : m.vk_notifications_connect_first()
	);
	const pwa = getPwaService();
	let showVkModal = $state(false);
	// Link to the group's chat where the user grants "allow messages". Built from
	// the build-time group id, so it may be empty if VK notifications were not
	// configured for this deployment — the modal hides the button then.
	const vkGroupUrl = PUBLIC_VK_GROUP_ID ? `https://vk.ru/im?sel=-${PUBLIC_VK_GROUP_ID}` : null;

	// Where a denied permission is lifted depends on how the app is open. An
	// installed app has no address bar: iOS keeps a Home Screen app's permission
	// in the system Notifications settings, "just like any other app"
	// (https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/),
	// and an Android WebAPK in its app settings. Only a browser tab has the site
	// settings behind the address-bar icon.
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
				const { data } = await checkPushSubscription({ query: { endpoint } });
				return data?.subscribed ?? false;
			},
			async register(registration) {
				await pushSubscribeMutation.mutateAsync({ body: registration });
			},
			async unregister(endpoint) {
				await pushUnsubscribeMutation.mutateAsync({ query: { endpoint } });
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
		// No success toast: the switch already sits in its new position, and a
		// switch is expected to take effect on its own
		// (https://www.nngroup.com/articles/toggle-switch-guidelines/).
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

	function toggleReceiveVk(checked: boolean) {
		receiveVk = checked;
		updateSettings(
			{
				receive_vk_notifications: receiveVk
			},
			() => {
				// Roll back to the effective state, not the raw flag: if VK was
				// unlinked while the request was in flight, restoring the raw `true`
				// would force the disabled toggle back ON — the misleading state this
				// card avoids. Mirrors the receiveVk derived above.
				receiveVk = hasVkAccount && (user.settings.receive_vk_notifications ?? false);
			}
		);
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

<VkNotificationsModal bind:open={showVkModal} {vkGroupUrl} />
