import type { CurrentUserDto } from '#lib/api/generated/index.js';
import type { DevicePushState } from '#lib/services/pushDevice.svelte.js';

import { m } from '#lib/paraglide/messages.js';

type ChannelOwner = Pick<CurrentUserDto, 'settings' | 'social_identities'>;

export function notificationsStatus(
	devicePush: DevicePushState,
	user: ChannelOwner
): string | undefined {
	const linked = new Set(user.social_identities.map((identity) => identity.provider));
	const vkOn = linked.has('vk') && user.settings.receive_vk_notifications;
	const telegramOn = linked.has('telegram') && user.settings.receive_telegram_notifications;

	if (devicePush === 'on' || vkOn || telegramOn) {
		return m.notifications_status_on();
	}
	if (devicePush === 'unknown') {
		return undefined;
	}
	return m.notifications_status_off();
}
