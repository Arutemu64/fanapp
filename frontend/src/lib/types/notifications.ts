import type { NotificationDto } from '$lib/api/client';

export type NotificationDTO = NotificationDto;

/**
 * Streamed seed for the app-shell bell: the capped dropdown preview plus the true
 * unread total. Produced by the (app) layout load and consumed by the bell; `null`
 * when the bell can't be seeded (guest or offline), where the SSE stream fills it.
 */
export interface NotificationSeed {
	preview: NotificationDTO[];
	unreadCount: number;
}
