// Load feedback in pages to avoid fetching the entire backlog at once.
export const FEEDBACK_PAGE_SIZE = 20;

// Fetch one extra item to determine whether a next page exists.
export const FEEDBACK_PAGE_REQUEST_LIMIT = FEEDBACK_PAGE_SIZE + 1;
