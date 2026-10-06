<script lang="ts">
	import type { CurrentUserDto, UpdateUserSettingsInput } from '$lib/api/generated';

	import { resolve } from '$app/paths';
	import { PUBLIC_VAPID_KEY, PUBLIC_VK_GROUP_ID } from '$env/static/public';
	import { createApiClient } from '$lib/api';
	// `checkSubscription` and `sendTestNotification` are aliased so they don't
	// clash with this component's own handlers of the same name below.
	import {
		checkSubscription as checkPushSubscription,
		sendTestNotification as sendTestPushNotification,
		subscribe,
		unsubscribe,
		updateCurrentUserSettings
	} from '$lib/api/generated';
	import MenuGroup from '$lib/components/MenuGroup.svelte';
	import { Button } from '$lib/components/ui/button';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import * as Sentry from '@sentry/sveltekit';
	import { onMount } from 'svelte';

	import { urlBase64ToUint8Array } from './push';
	import SettingsSection from './SettingsSection.svelte';
	import SwitchRow from './SwitchRow.svelte';
	import VkNotificationsModal from './VkNotificationsModal.svelte';

	interface Props {
		user: CurrentUserDto;
		onSettingsUpdate?: () => void;
	}

	let { user, onSettingsUpdate }: Props = $props();

	const client = createApiClient();

	// Every control here writes to the server (push subscribe/unsubscribe, settings
	// PATCH, test send) — online only. The current toggle states still render.
	const offlineGate = offlineWriteGate();

	let isSubscribed = $state(false);
	// Once the browser permission is "denied" it never prompts again, so the
	// toggle is a dead end — surface a persistent hint on how to unblock instead.
	let notificationsBlocked = $state(false);
	// In-app browsers (Telegram, VK, Instagram, …) run a WebView without Service
	// Worker / Push support, so push can never work there — and on Android they
	// report a plain Chrome UA, so we detect the missing capability rather than
	// sniffing the user agent. Surfaces a hint to open the app in a real browser
	// instead of letting the toggle fail with a generic error.
	let pushUnsupported = $state(false);
	const toastService = getToastService();
	let isLoading = $state(true);
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
	let isSavingSettings = $state(false);
	let isSendingTest = $state(false);
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

	async function checkSubscription() {
		try {
			notificationsBlocked =
				typeof Notification !== 'undefined' && Notification.permission === 'denied';
			if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
				pushUnsupported = true;
				isLoading = false;
				return;
			}
			const registration = await navigator.serviceWorker.ready;
			const subscription = await registration.pushManager.getSubscription();

			if (!subscription) {
				isSubscribed = false;
				return;
			}

			// The browser has a local subscription; confirm the server still knows
			// about this exact endpoint, otherwise treat it as not subscribed so the
			// user can re-register (e.g. after the server lost the subscription).
			const { data } = await checkPushSubscription({
				client,
				query: { endpoint: subscription.endpoint }
			});
			isSubscribed = data?.subscribed ?? false;
		} catch (error) {
			console.error('Error checking push subscription:', error);
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		void checkSubscription();
	});

	// Best-effort rollback of a browser push subscription. A failing unsubscribe is
	// itself a cleanup problem — it must not propagate and be reported as the
	// original failure, whose real cause was already captured at the call site.
	async function discardSubscription(subscription: PushSubscription) {
		try {
			await subscription.unsubscribe();
		} catch (error) {
			console.error('Failed to roll back push subscription:', error);
		}
	}

	async function toggleSubscription() {
		if (isSubscribed) {
			try {
				isLoading = true;
				const registration = await navigator.serviceWorker.ready;
				const subscription = await registration.pushManager.getSubscription();
				if (subscription) {
					// Remove the matching subscription on the backend before unsubscribing locally.
					const { error, response } = await unsubscribe({
						client,
						body: {
							endpoint: subscription.endpoint
						}
					});

					if (error || !response?.ok) {
						console.error('Failed to remove subscription from server:', error);
					}

					await subscription.unsubscribe();
					isSubscribed = false;
					onSettingsUpdate?.();
				}
			} catch (e) {
				console.error('Failed to unsubscribe', e);
				toastService.add('Не удалось отключить уведомления', 'error');
			} finally {
				isLoading = false;
			}
			return;
		}

		if (pwa.isApplePlatform && !pwa.isInstalled) {
			pwa.showInstallDialog();
			return;
		}

		isLoading = true;
		// Flips once the browser subscription exists, so the catch below can tell a
		// genuine subscribe / service-worker failure from a later backend-request throw.
		let browserSubscribed = false;
		try {
			if (typeof Notification === 'undefined') {
				toastService.add('Твой браузер не поддерживает уведомления', 'error');
				return;
			}

			// PUBLIC_VAPID_KEY is baked in at build time, so it may be empty if push
			// notifications were not configured for this deployment.
			const vapidKey = PUBLIC_VAPID_KEY;
			if (!vapidKey) {
				// Deploy misconfig, not a user problem: the build shipped without a VAPID
				// key, so push can never work here. One grouped GlitchTip issue surfaces it.
				Sentry.captureMessage('Push subscribe blocked: missing VAPID key', {
					level: 'warning',
					tags: { push_outcome: 'no_vapid_key' }
				});
				toastService.add('Уведомления сейчас недоступны', 'error');
				return;
			}

			if (Notification.permission === 'default') {
				const permission = await Notification.requestPermission();
				if (permission !== 'granted') {
					notificationsBlocked = permission === 'denied';
					// User choice, not a bug — a breadcrumb (buffered, free) is enough to
					// give context if a real error fires later in this attempt.
					Sentry.addBreadcrumb({
						category: 'push',
						level: 'info',
						message: 'Push permission not granted',
						data: { permission }
					});
					toastService.add('Уведомления не разрешены', 'error');
					return;
				}
			} else if (Notification.permission === 'denied') {
				notificationsBlocked = true;
				toastService.add('Уведомления заблокированы', 'error');
				return;
			}

			notificationsBlocked = false;

			const registration = await navigator.serviceWorker.ready;

			const subscription = await registration.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: urlBase64ToUint8Array(vapidKey)
			});
			browserSubscribed = true;

			const subJson = subscription.toJSON();
			const endpoint = subJson.endpoint;
			const p256dh = subJson.keys?.p256dh;
			const auth = subJson.keys?.auth;

			if (!endpoint || !p256dh || !auth) {
				// The browser handed back a subscription missing the fields the backend
				// needs — a real failure worth surfacing, not a user choice.
				Sentry.captureMessage('Push subscribe returned an incomplete subscription', {
					level: 'warning',
					tags: { push_outcome: 'invalid_subscription' }
				});
				toastService.add('Не удалось подключить устройство. Попробуй ещё раз', 'error');
				await discardSubscription(subscription);
				return;
			}

			const { error, response } = await subscribe({
				client,
				body: {
					endpoint,
					p256dh,
					auth
				}
			});

			if (error || !response?.ok) {
				console.error('API Error:', error);
				// The browser subscribed but the backend rejected it, so push stays off
				// despite a granted permission — the failure mode worth catching.
				Sentry.captureMessage('Push subscribe rejected by backend', {
					level: 'warning',
					tags: { push_outcome: 'backend_rejected' },
					extra: { status: response?.status }
				});
				toastService.add('Не удалось включить уведомления. Попробуй ещё раз', 'error');
				await discardSubscription(subscription);
				return;
			}

			isSubscribed = true;
			onSettingsUpdate?.();
		} catch (error: unknown) {
			console.error('Failed to subscribe:', error);
			// Classify by where it threw: before the browser subscription exists it's a
			// genuine subscribe / service-worker failure; after, the only throw left is
			// the backend registration request, which is a different failure mode.
			Sentry.captureException(error, {
				tags: { push_outcome: browserSubscribed ? 'backend_request_threw' : 'subscribe_threw' }
			});
			toastService.add('Не удалось включить уведомления', 'error');
		} finally {
			isLoading = false;
		}
	}

	async function updateSettings(
		nextSettings: Partial<UpdateUserSettingsInput>,
		rollback: () => void
	) {
		isSavingSettings = true;
		const { error, response } = await updateCurrentUserSettings({
			client,
			body: nextSettings
		});

		if (error || !response?.ok) {
			console.error('API Error:', error);
			toastService.add('Не удалось обновить настройки', 'error');
			rollback();
		} else {
			// No success toast: the switch already sits in its new position, and a
			// switch is expected to take effect on its own
			// (https://www.nngroup.com/articles/toggle-switch-guidelines/).
			onSettingsUpdate?.();
		}
		isSavingSettings = false;
	}

	function toggleReceiveAll(checked: boolean) {
		receiveAll = checked;
		void updateSettings(
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
		void updateSettings(
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

	async function sendTestNotification() {
		if (isSendingTest) {
			return;
		}

		try {
			isSendingTest = true;

			const { error, response } = await sendTestPushNotification({ client });

			if (error || !response?.ok) {
				console.error('API Error:', error);
				toastService.add('Не удалось отправить тестовое уведомление', 'error');
				return;
			}

			toastService.add(
				'Тест отправлен. Должны прийти тост, колокольчик и системное пуш-уведомление.',
				'success'
			);
		} catch (error) {
			console.error('Failed to send test notification:', error);
			toastService.add('Не удалось отправить тест по каналам уведомлений', 'error');
		} finally {
			isSendingTest = false;
		}
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
				checked={isSubscribed}
				disabled={isLoading || pushUnsupported || offlineGate.disabled}
				disabledHint={offlineGate.title}
				onCheckedChange={() => {
					void toggleSubscription();
				}}
			>
				{#if pushUnsupported}
					<p class="mt-2 text-sm leading-relaxed text-muted-foreground">
						Чтобы получать уведомления, открой приложение в браузере — Chrome или Safari. Во
						встроенном браузере они не работают.
					</p>
				{:else if notificationsBlocked}
					<p class="mt-2 text-sm leading-relaxed text-destructive">{blockedHint}</p>
				{/if}
			</SwitchRow>

			<SwitchRow
				id="vk-notifications"
				title="ВКонтакте"
				description={vkDescription}
				checked={receiveVk}
				disabled={isSavingSettings || !hasVkAccount || offlineGate.disabled}
				disabledHint={offlineGate.title}
				onCheckedChange={toggleReceiveVk}
			>
				<div class="flex flex-wrap gap-x-4">
					{#if !hasVkAccount}
						<a
							href={resolve('/profile/account')}
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
				disabled={isSavingSettings || offlineGate.disabled}
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
			disabled={isSendingTest || offlineGate.disabled}
			title={offlineGate.title}
			onclick={sendTestNotification}
		>
			{#if isSendingTest}
				Отправка…
			{:else}
				Проверить уведомления
			{/if}
		</Button>
	</div>
</div>

<VkNotificationsModal bind:open={showVkModal} {vkGroupUrl} />
