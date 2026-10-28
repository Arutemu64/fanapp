import type { CurrentUserDto } from '#lib/api/generated/index.js';
import type { DevicePushState } from '#lib/services/pushDevice.svelte.js';

import { m } from '#lib/paraglide/messages.js';
import { hasMessengerNotifications } from '#lib/utils/users.js';

type ChannelOwner = Pick<CurrentUserDto, 'settings' | 'social_identities'>;

export function notificationsStatus(
	devicePush: DevicePushState,
	user: ChannelOwner
): string | undefined {
	if (devicePush === 'on' || hasMessengerNotifications(user)) {
		return m.notifications_status_on();
	}
	if (devicePush === 'unknown') {
		return undefined;
	}
	return m.notifications_status_off();
}
