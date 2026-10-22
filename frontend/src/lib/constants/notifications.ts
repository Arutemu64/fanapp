// Cap the bell badge so a large unread total stays legible (shown as "99+").
export const NOTIFICATION_BADGE_MAX = 99;

// On the dedicated page, load notifications in pages to avoid fetching the entire list at once.
export const NOTIFICATION_PAGE_SIZE = 20;

// Broadcast history (organizer tool) pages the sent mailings the same way.
export const BROADCAST_PAGE_SIZE = 10;

// Mirrors the server's cap on a broadcast's text (BROADCAST_BODY_MAX_LENGTH in
// backend send_broadcast.py), which keeps the Web Push payload under its size limit.
export const BROADCAST_BODY_MAX_LENGTH = 500;
