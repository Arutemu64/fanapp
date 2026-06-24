import { error as kitError } from '@sveltejs/kit';
import type { components } from '$lib/api/v1';

// The closed set of error codes the API can return, generated from the backend
// OpenAPI spec (ErrorMessage.code enum). Drives both typo safety on the message
// dictionary and the compile-time drift guard at the bottom of this file.
type ApiErrorCode = components['schemas']['ErrorMessage']['code'];

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

// Pydantic error "type" -> short Russian reason. Kept lowercase so it reads
// naturally when appended after a field label ("поле «пароль»: ...").
const VALIDATION_TYPE_MESSAGES: Record<string, string> = {
	missing: 'не заполнено',
	string_too_short: 'слишком короткое значение',
	string_too_long: 'слишком длинное значение',
	string_pattern_mismatch: 'неверный формат',
	value_error: 'неверный формат',
	greater_than: 'значение слишком маленькое',
	greater_than_equal: 'значение слишком маленькое',
	less_than: 'значение слишком большое',
	less_than_equal: 'значение слишком большое',
	int_parsing: 'нужно число',
	int_type: 'нужно число',
	float_parsing: 'нужно число',
	float_type: 'нужно число'
};

function capitalize(text: string): string {
	return text.charAt(0).toUpperCase() + text.slice(1);
}

function getValidationMessage(details: ApiErrorDetails): string {
	const firstError = getValidationErrors(details)[0];
	if (!firstError) {
		return 'Проверь заполнение формы';
	}

	const fieldLabel = getFieldLabel(firstError.loc);
	const reason = VALIDATION_TYPE_MESSAGES[firstError.type];

	if (fieldLabel && reason) {
		return `Проверь поле «${fieldLabel}»: ${reason}`;
	}
	if (fieldLabel) {
		return `Проверь поле «${fieldLabel}»`;
	}
	if (reason) {
		return capitalize(reason);
	}
	return 'Проверь заполнение формы';
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

// Dictionary: error code -> user-facing message. `satisfies` keeps the literal
// keys (so the drift guard below can see which codes are covered) while checking
// every key is a real ApiErrorCode — a typo'd code is a compile error.
const ERROR_MESSAGES = {
	ALREADY_VOTED_IN_THIS_NOMINATION: 'Ты уже голосовал в этой номинации',
	CAPTCHA_VERIFICATION_FAILED: 'Не удалось пройти проверку. Попробуй ещё раз.',
	CURRENT_EVENT_NOT_ALLOWED: 'Это выступление нельзя отметить как текущее',
	EMAIL_ALREADY_EXISTS: 'Этот адрес уже используется',
	EVENT_NOT_FOUND: 'Выступление не найдено',
	INCORRECT_PASSWORD: 'Неверная почта или пароль',
	INVALID_CREDENTIALS: 'Неверная почта или пароль',
	INVALID_EMAIL: 'Неверный адрес эл. почты',
	INVALID_OTP_CODE: 'Неверный или устаревший код',
	INVALID_TELEGRAM_AUTH_PAYLOAD: 'Не удалось подтвердить Telegram',
	OUTDATED_SCHEDULE_CHANGE: 'Программа уже изменилась, обнови страницу',
	PUSH_SUBSCRIPTION_ALREADY_EXISTS: 'Это устройство уже подключено к push-уведомлениям',
	SAME_EVENTS_ARE_NOT_ALLOWED: 'Нельзя выбрать одно и то же выступление',
	SKIPPED_EVENT_NOT_ALLOWED: 'Пропущенное выступление нельзя отметить как текущее',
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
	USER_HAS_NO_EMAIL: 'Сначала добавь почту к аккаунту',
	USER_NOT_AUTHENTICATED: 'Нужно войти в аккаунт',
	USER_NOT_FOUND: 'Аккаунт не найден',
	USERNAME_ALREADY_TAKEN: 'Это имя пользователя уже занято',
	USERNAME_PROFANITY: 'Псевдоним содержит недопустимые слова',
	VOTE_NOT_FOUND: 'Голос не найден'
} satisfies Partial<Record<ApiErrorCode, string>>;

// Codes carrying a `retry_after` detail; all share the same formatted message.
const RETRY_AFTER_CODES = [
	'EMAIL_CODE_REQUEST_TOO_FAST',
	'SCHEDULE_EDIT_TOO_FAST',
	'TOO_MANY_ATTEMPTS',
	'TOO_MANY_OTP_ATTEMPTS',
	'TOO_MANY_LOGIN_ATTEMPTS'
] as const satisfies readonly ApiErrorCode[];

// Codes intentionally left to the generic fallback toast: not individually
// actionable by the user (server/internal errors) or surfaced by dedicated UI
// elsewhere (not-found states). Listed explicitly so the drift guard passes.
// Consumed only by the type-level guard below, hence not read at runtime.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const GENERIC_FALLBACK_CODES = [
	'AUTHENTICATION_ERROR',
	'HTTP_ERROR',
	'INTERNAL_ERROR',
	'APP_SETTINGS_NOT_FOUND',
	'NOMINATION_NOT_FOUND',
	'PARTICIPANT_NOT_FOUND',
	'PUSH_SUBSCRIPTION_NOT_FOUND',
	'SCHEDULE_CHANGE_NOT_FOUND',
	'SUBSCRIPTION_NOT_FOUND'
] as const satisfies readonly ApiErrorCode[];

export function getApiErrorDetail(error: unknown): string | null {
	const payload = getApiErrorPayload(error);
	if (!payload) {
		return null;
	}

	// Dictionary covers most codes. Cast because payload.code is an unverified
	// wire string, not a known ApiErrorCode.
	const simple = (ERROR_MESSAGES as Record<string, string | undefined>)[payload.code];
	if (simple) {
		return simple;
	}

	const details = payload.details ?? {};
	if ((RETRY_AFTER_CODES as readonly string[]).includes(payload.code)) {
		return formatRetryAfter(details.retry_after);
	}
	if (payload.code === 'ACCESS_DENIED') {
		return getAccessDeniedMessage(details);
	}
	if (payload.code === 'VALIDATION_ERROR') {
		return getValidationMessage(details);
	}
	return null;
}

export function getApiErrorCode(error: unknown): string | null {
	return getApiErrorPayload(error)?.code ?? null;
}

/**
 * Throw a SvelteKit error from a failed openapi-fetch call, so a `load` failure
 * speaks the same language as a form/toast failure. Maps the API error `code` to
 * the shared Russian copy and reuses the real HTTP status; `code` rides along on
 * `App.Error` for the error page and Sentry. Usage:
 * `if (apiError) throwApiError(apiError, response, 'Не удалось загрузить …');`
 */
export function throwApiError(
	apiError: unknown,
	response: { status: number } | undefined,
	fallback: string
): never {
	// Clamp to an error status: a non-error response here means data was missing
	// without an HTTP error, which we treat as a server-side problem.
	const status = response && response.status >= 400 ? response.status : 500;
	const message = getApiErrorDetail(apiError) ?? fallback;
	const code = getApiErrorCode(apiError);
	return kitError(status, code ? { message, code } : { message });
}

// Compile-time drift guard: every client-facing code must be covered by the
// dictionary, the retry-after / access-denied / validation handling, or the
// explicit generic-fallback list. If the backend adds a new code that is none of
// these, UnhandledCode stops being `never` and this line fails `pnpm check` —
// naming the missing code(s). Resolve by adding copy to ERROR_MESSAGES or
// listing the code in GENERIC_FALLBACK_CODES.
type HandledCode =
	| keyof typeof ERROR_MESSAGES
	| (typeof RETRY_AFTER_CODES)[number]
	| (typeof GENERIC_FALLBACK_CODES)[number]
	| 'ACCESS_DENIED'
	| 'VALIDATION_ERROR';
type UnhandledCode = Exclude<ApiErrorCode, HandledCode>;
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _exhaustiveErrorCodes: UnhandledCode extends never ? true : UnhandledCode = true;
