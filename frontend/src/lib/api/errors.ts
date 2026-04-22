type ApiErrorDetails = Record<string, unknown>;

interface ApiErrorPayload {
	code: string;
	details?: ApiErrorDetails;
}

interface ApiValidationErrorDetail {
	loc: Array<string | number>;
	type: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return Boolean(value) && typeof value === 'object';
}

function getApiErrorPayload(error: unknown): ApiErrorPayload | null {
	if (!isRecord(error) || typeof error.code !== 'string') {
		return null;
	}

	const details = isRecord(error.details) ? error.details : {};
	return {
		code: error.code,
		details
	};
}

function getValidationErrors(details: ApiErrorDetails): ApiValidationErrorDetail[] {
	const rawErrors = details.errors;
	if (!Array.isArray(rawErrors)) {
		return [];
	}

	return rawErrors.filter((item): item is ApiValidationErrorDetail => {
		return isRecord(item) && Array.isArray(item.loc) && typeof item.type === 'string';
	});
}

function getFieldLabel(path: Array<string | number>): string | null {
	const lastSegment = path
		.filter((segment): segment is string => typeof segment === 'string')
		.filter((segment) => !['body', 'query', 'path'].includes(segment))
		.at(-1);

	if (!lastSegment) {
		return null;
	}

	const labels: Record<string, string> = {
		email: 'эл. почта',
		new_email: 'эл. почта',
		password: 'пароль',
		old_password: 'текущий пароль',
		new_password: 'новый пароль',
		code: 'код',
		barcode: 'номер билета',
		username: 'имя пользователя'
	};

	return labels[lastSegment] ?? null;
}

function formatRetryAfter(value: unknown): string {
	if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
		return `Попробуй ещё раз через ${Math.ceil(value)} сек.`;
	}

	return 'Попробуй ещё раз позже.';
}

function getAccessDeniedMessage(details: ApiErrorDetails): string {
	switch (details.reason) {
		case 'VOTING_TICKET_REQUIRED':
			return 'Для голосования привяжи билет.';
		case 'VOTING_DISABLED':
			return 'Голосование сейчас отключено.';
		case 'MAILING_DELETE_FORBIDDEN':
			return 'Нельзя удалить эту рассылку.';
		default:
			return 'Нет доступа к этому действию.';
	}
}

// -- Простой словарь: код ошибки → сообщение для пользователя --
const ERROR_MESSAGES: Record<string, string> = {
	ALREADY_VOTED_IN_THIS_NOMINATION: 'Ты уже голосовал в этой номинации',
	EMAIL_ALREADY_EXISTS: 'Этот адрес уже используется',
	INCORRECT_PASSWORD: 'Неверная почта или пароль',
	INVALID_CREDENTIALS: 'Неверная почта или пароль',
	INVALID_OTP_CODE: 'Неверный или устаревший код',
	INVALID_TELEGRAM_AUTH_PAYLOAD: 'Не удалось подтвердить Telegram',
	PUSH_SUBSCRIPTION_ALREADY_EXISTS: 'Это устройство уже подключено к push-уведомлениям',
	SUBSCRIPTION_ALREADY_EXISTS: 'Ты уже подписан на это выступление',
	TELEGRAM_ALREADY_LINKED_TO_ANOTHER_USER: 'Этот Telegram уже привязан к другому аккаунту',
	TELEGRAM_CANNOT_BE_UNLINKED_WITHOUT_EMAIL:
		'Сначала добавь почту, чтобы не потерять доступ к аккаунту',
	TICKET_ALREADY_USED: 'Этот билет уже использован',
	TICKET_NOT_FOUND: 'Билет не найден',
	TICKET_NOT_LINKED: 'Сначала привяжи билет',
	USER_ALREADY_EXISTS: 'Этот адрес уже используется',
	USER_ALREADY_HAS_TELEGRAM_LINKED: 'К аккаунту уже привязан Telegram',
	USER_ALREADY_HAS_TICKET_LINKED: 'У тебя уже привязан билет',
	USER_NOT_AUTHENTICATED: 'Нужно войти в аккаунт',
	USER_NOT_FOUND: 'Аккаунт не найден',
	USERNAME_ALREADY_TAKEN: 'Это имя пользователя уже занято'
};

export function getApiErrorCode(error: unknown): string | null {
	return getApiErrorPayload(error)?.code ?? null;
}

export function getApiErrorDetail(error: unknown): string | null {
	const payload = getApiErrorPayload(error);
	if (!payload) {
		return null;
	}

	// Простой словарь — большинство кодов
	const simple = ERROR_MESSAGES[payload.code];
	if (simple) {
		return simple;
	}

	// Коды, требующие дополнительной логики
	const details = payload.details ?? {};
	switch (payload.code) {
		case 'SCHEDULE_EDIT_TOO_FAST':
		case 'NOTIFICATION_RETRY_AFTER':
			return formatRetryAfter(details.retry_after);
		case 'ACCESS_DENIED':
			return getAccessDeniedMessage(details);
		case 'VALIDATION_ERROR': {
			const firstError = getValidationErrors(details)[0];
			const fieldLabel = firstError ? getFieldLabel(firstError.loc) : null;
			return fieldLabel ? `Проверь поле «${fieldLabel}»` : 'Проверь заполнение формы';
		}
		default:
			return null;
	}
}
