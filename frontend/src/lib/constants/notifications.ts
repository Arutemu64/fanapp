// Дропдаун оставляем коротким, чтобы список было удобно читать на телефоне.
export const NOTIFICATION_PREVIEW_LIMIT = 5;

// На отдельной странице показываем уведомления порциями, чтобы не грузить весь список сразу.
export const NOTIFICATION_PAGE_SIZE = 20;

// Запрашиваем на один элемент больше, чтобы понять, есть ли следующая страница.
export const NOTIFICATION_PAGE_REQUEST_LIMIT = NOTIFICATION_PAGE_SIZE + 1;
