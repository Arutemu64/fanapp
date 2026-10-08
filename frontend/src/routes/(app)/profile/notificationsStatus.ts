import type { CurrentUserDto } from '#lib/api/generated/index.js';
import type { DevicePushState } from '#lib/utils/pushSubscription.js';

type ChannelOwner = Pick<CurrentUserDto, 'settings' | 'social_identities'>;

/**
 * The hub row's value: «Включены» when any channel reaches the user, «Выключены»
 * when none does. The channels mirror the backend's delivery: push needs a live
 * subscription on this device; VK and Telegram need the account linked and the
 * channel's setting on (SendNotification checks the setting, each notifier the
 * link). Telegram has no switch on the notifications page, but it still delivers,
 * so it counts — leaving it out would read «Выключены» to someone getting messages.
 *
 * Unknown device push with no social channel on returns nothing: a guess would
 * be the one thing this line must not do.
 */
export function notificationsStatus(
	devicePush: DevicePushState,
	user: ChannelOwner
): string | undefined {
	const linked = new Set(user.social_identities.map((identity) => identity.provider));
	const vkOn = linked.has('vk') && user.settings.receive_vk_notifications === true;
	const telegramOn =
		linked.has('telegram') && user.settings.receive_telegram_notifications === true;

	if (devicePush === 'on' || vkOn || telegramOn) {
		return 'Включены';
	}
	if (devicePush === 'unknown') {
		return undefined;
	}
	return 'Выключены';
}
