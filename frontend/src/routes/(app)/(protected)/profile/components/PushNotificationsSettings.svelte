<script lang="ts">
	import { PUBLIC_VAPID_KEY, PUBLIC_VK_GROUP_ID } from '$app/env/public';
	import { resolve } from '$app/paths';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { CurrentUserDto, UpdateUserSettingsInput } from '#lib/api/generated/index.js';

	import {
		getCurrentUserQueryKey,
		sendTestNotificationMutation,
		subscribeMutation,
		unsubscribeMutation,
		updateCurrentUserSettingsMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	// Aliased so it doesn't clash with this component's own handler of the same name.
	import { checkSubscription as checkPushSubscription } from '#lib/api/generated/index.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { PushDevice, type PushToggleOutcome } from '#lib/services/pushDevice.svelte.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import SettingsSection from './SettingsSection.svelte';
	import SwitchRow from './SwitchRow.svelte';
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
		...subscribeMutation(),
		onSuccess: refreshUser
	}));
	const pushUnsubscribeMutation = createMutation(() => ({
		...unsubscribeMutation(),
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
	// Writable deriveds: a toggle overrides them optimistically, and they snap back
	// to the server copy whenever `user` refreshes (Svelte "Overriding derived values").
	let receiveAll = $derived(user.settings.receive_all_announcements ?? false);
	let receiveVk = $derived(hasVkAccount && (user.settings.receive_vk_notifications ?? false));
	let vkDescription = $derived(
		hasVkAccount
			? 'Получать сообщения от сообщества во ВКонтакте.'
			: 'Сначала подключи ВКонтакте в настройках аккаунта.'
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
			return 'Уведомления заблокированы в браузере. Открой настройки сайта (значок замка рядом с адресом) и разреши уведомления.';
		}
		if (pwa.isApplePlatform) {
			return 'Уведомления выключены в настройках устройства. Открой Настройки → Уведомления → ФАН ФАН и разреши уведомления.';
		}
		return 'Уведомления выключены в настройках телефона. Открой настройки приложения ФАН ФАН и разреши уведомления.';
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
				await pushUnsubscribeMutation.mutateAsync({ body: { endpoint } });
			}
		}
	});

	onMount(() => {
		void pushDevice.refresh();
	});

	const toggleFailureCopy: Record<Exclude<PushToggleOutcome, 'enabled' | 'disabled'>, string> = {
		unsupported: 'Твой браузер не поддерживает уведомления',
		unavailable: 'Уведомления сейчас недоступны',
		blocked: 'Уведомления заблокированы',
		'not-granted': 'Уведомления не разрешены',
		incomplete: 'Не удалось подключить устройство. Попробуй ещё раз',
		rejected: 'Не удалось включить уведомления. Попробуй ещё раз',
		failed: 'Не удалось включить уведомления',
		'disable-failed': 'Не удалось отключить уведомления'
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
					toastService.add('Не удалось обновить настройки', 'error');
					rollback();
				}
			}
		);
	}

	function toggleReceiveAll(checked: boolean) {
		receiveAll = checked;
		updateSettings(
			{
				receive_all_announcements: receiveAll
			},
			() => {
				receiveAll = user.settings.receive_all_announcements ?? false;
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
					toastService.add(
						'Тест отправлен. Должны прийти тост, колокольчик и системное пуш-уведомление.',
						'success'
					);
				},
				onError: () => toastService.add('Не удалось отправить тестовое уведомление', 'error')
			}
		);
	}
</script>

<div class="flex flex-col gap-6">
	<p class="text-sm leading-5 text-muted-foreground">
		Настрой уведомления, чтобы не пропустить анонсы и важные сообщения.
	</p>

	<SettingsSection title="Каналы">
		<MenuGroup class="divide-y divide-border">
			<SwitchRow
				id="push-this-device"
				title="На этом устройстве"
				description="Приходят как обычные уведомления телефона, даже когда приложение закрыто."
				checked={pushDevice.state === 'on'}
				disabled={pushDevice.isBusy || pushDevice.state === 'unsupported' || offlineGate.disabled}
				disabledHint={offlineGate.title}
				onCheckedChange={() => {
					void toggleSubscription();
				}}
			>
				{#if pushDevice.state === 'unsupported'}
					<p class="mt-2 text-sm leading-relaxed text-muted-foreground">
						Чтобы получать уведомления, открой приложение в браузере — Chrome или Safari. Во
						встроенном браузере они не работают.
					</p>
				{:else if pushDevice.state === 'blocked'}
					<p class="mt-2 text-sm leading-relaxed text-destructive">{blockedHint}</p>
				{/if}
			</SwitchRow>

			<SwitchRow
				id="vk-notifications"
				title="ВКонтакте"
				description={vkDescription}
				checked={receiveVk}
				disabled={settingsMutation.isPending || !hasVkAccount || offlineGate.disabled}
				disabledHint={offlineGate.title}
				onCheckedChange={toggleReceiveVk}
			>
				<div class="flex flex-wrap gap-x-4">
					{#if !hasVkAccount}
						<a
							href={resolve('profile/account')}
							class="inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline"
						>
							Подключить ВКонтакте
						</a>
					{/if}
					<button
						type="button"
						class="inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline"
						onclick={() => (showVkModal = true)}
					>
						Как это работает?
					</button>
				</div>
			</SwitchRow>
		</MenuGroup>
	</SettingsSection>

	<SettingsSection title="Типы уведомлений">
		<MenuGroup>
			<SwitchRow
				id="all-announcements"
				title="Все анонсы"
				description="Получать уведомления о начале каждого выступления."
				checked={receiveAll}
				disabled={settingsMutation.isPending || offlineGate.disabled}
				disabledHint={offlineGate.title}
				onCheckedChange={toggleReceiveAll}
			/>
		</MenuGroup>
	</SettingsSection>

	<div>
		<p class="mb-3 text-sm leading-relaxed text-muted-foreground">
			Попробуй отправить себе пробное уведомление, чтобы убедиться, что всё работает.
		</p>
		<Button
			variant="outline"
			class="w-full sm:w-auto"
			disabled={testMutation.isPending || offlineGate.disabled}
			title={offlineGate.title}
			onclick={sendTestNotification}
		>
			{#if testMutation.isPending}
				<Spinner data-icon="inline-start" />
				Отправка…
			{:else}
				Проверить уведомления
			{/if}
		</Button>
	</div>
</div>

<VkNotificationsModal bind:open={showVkModal} {vkGroupUrl} />
