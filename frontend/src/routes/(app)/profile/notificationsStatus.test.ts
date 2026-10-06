import type { SocialProvider } from '$lib/api/generated';

import { describe, expect, it } from 'vitest';

import { notificationsStatus } from './notificationsStatus';

function user(
	providers: SocialProvider[],
	settings: { receive_vk_notifications?: boolean; receive_telegram_notifications?: boolean } = {}
) {
	return {
		social_identities: providers.map((provider) => ({ provider })),
		settings: {
			receive_all_announcements: true,
			receive_vk_notifications: true,
			receive_telegram_notifications: true,
			...settings
		}
	} as Parameters<typeof notificationsStatus>[1];
}

describe('notificationsStatus', () => {
	it('is on with push on this device', () => {
		expect(notificationsStatus('on', user([]))).toBe('Включены');
	});

	it('is on through linked VK with its setting on, even with push off', () => {
		expect(notificationsStatus('off', user(['vk']))).toBe('Включены');
	});

	it('is on through linked Telegram, which has no switch but still delivers', () => {
		expect(notificationsStatus('off', user(['telegram']))).toBe('Включены');
	});

	it('is off when a linked channel has its setting off', () => {
		expect(notificationsStatus('off', user(['vk'], { receive_vk_notifications: false }))).toBe(
			'Выключены'
		);
	});

	it('ignores a setting that is on for an unlinked account', () => {
		expect(notificationsStatus('off', user([]))).toBe('Выключены');
	});

	it('says nothing when push is unknown and no other channel is on', () => {
		expect(notificationsStatus('unknown', user([]))).toBeUndefined();
	});

	it('is still on through VK when push is unknown', () => {
		expect(notificationsStatus('unknown', user(['vk']))).toBe('Включены');
	});
});
