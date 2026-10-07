// Load schedule changes in pages to avoid fetching the entire audit log at once.
export const SCHEDULE_CHANGES_PAGE_SIZE = 20;

// Fetch one extra item to determine whether a next page exists.
export const SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT = SCHEDULE_CHANGES_PAGE_SIZE + 1;
