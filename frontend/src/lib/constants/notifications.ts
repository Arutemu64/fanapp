// Keep the dropdown short so the list is easy to read on mobile.
export const NOTIFICATION_PREVIEW_LIMIT = 5;

// On the dedicated page, load notifications in pages to avoid fetching the entire list at once.
export const NOTIFICATION_PAGE_SIZE = 20;

// Fetch one extra item to determine whether a next page exists.
export const NOTIFICATION_PAGE_REQUEST_LIMIT = NOTIFICATION_PAGE_SIZE + 1;
