import { error as kitError } from '@sveltejs/kit';
import { CancelledError } from '@tanstack/svelte-query';

import type { ErrorMessage } from '#lib/api/generated/index.js';

import { m } from '#lib/paraglide/messages.js';
import { anySignal, timeoutSignal } from '#lib/utils/fetchTimeout.js';

// The closed set of error codes the API can return, generated from the backend
// OpenAPI spec (ErrorMessage.code enum). Drives both typo safety on the message
// dictionary and the compile-time drift guard at the bottom of this file.
type ApiErrorCode = ErrorMessage['code'];

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

// The request field a Pydantic `loc` points at: its last named segment, past
// the leading `body` / `query` / `path` location. Only that first segment is a
// location — a field can itself be called `body` (the broadcast's
// `['body', 'body']`).
function getFieldName(path: Array<string | number>): string | null {
	const [location, ...rest] = path;
	const isLocation = typeof location === 'string' && ['body', 'query', 'path'].includes(location);
	const fieldPath = isLocation ? rest : path;

	const lastSegment = fieldPath
		.filter((segment): segment is string => typeof segment === 'string')
		.at(-1);

	return lastSegment ?? null;
}

function getFieldLabel(path: Array<string | number>): string | null {
	const fieldName = getFieldName(path);
	if (!fieldName) {
		return null;
	}

	const labels: Record<string, string> = {
		email: m.field_email(),
		new_email: m.field_email(),
		password: m.field_password(),
		old_password: m.field_old_password(),
		new_password: m.field_new_password(),
		code: m.field_code(),
		barcode: m.field_barcode(),
		username: m.field_username(),
		text: m.field_text(),
		amount: m.field_amount()
	};

	return labels[fieldName] ?? null;
}

// Pydantic error "type" -> short Russian reason. Kept lowercase so it reads
// naturally when appended after a field label ("поле «пароль»: ...").
const VALIDATION_TYPE_MESSAGES: Record<string, () => string> = {
	missing: m.validation_missing,
	string_too_short: m.validation_too_short,
	string_too_long: m.validation_too_long,
	string_pattern_mismatch: m.validation_bad_format,
	value_error: m.validation_bad_format,
	greater_than: m.validation_too_small,
	greater_than_equal: m.validation_too_small,
	less_than: m.validation_too_large,
	less_than_equal: m.validation_too_large,
	int_parsing: m.validation_number_required,
	int_type: m.validation_number_required,
	float_parsing: m.validation_number_required,
	float_type: m.validation_number_required
};

function capitalize(text: string): string {
	return text.charAt(0).toUpperCase() + text.slice(1);
}

function getValidationMessage(details: ApiErrorDetails): string {
	const firstError = getValidationErrors(details)[0];
	if (!firstError) {
		return m.validation_check_form();
	}

	const fieldLabel = getFieldLabel(firstError.loc);
	const reason = VALIDATION_TYPE_MESSAGES[firstError.type]?.();

	if (fieldLabel && reason) {
		return m.validation_check_field_reason({ fieldLabel, reason });
	}
	if (fieldLabel) {
		return m.validation_check_field({ fieldLabel });
	}
	if (reason) {
		return capitalize(reason);
	}
	return m.validation_check_form();
}

/**
 * The API error `code`, for a caller that branches on one. A query rethrows the
 * error body without its HTTP status, so a "not found" is told apart by code.
 */
export function getApiErrorCode(error: unknown): string | undefined {
	return getApiErrorPayload(error)?.code;
}

/**
 * What a VALIDATION_ERROR says about one request field, for showing under that
 * input instead of as a form-level message. `null` when the error is anything
 * else or names a different field — the caller then falls back to
 * getApiErrorDetail for the form as a whole.
 */
export function getApiFieldError(error: unknown, field: string): string | null {
	const payload = getApiErrorPayload(error);
	if (payload?.code !== 'VALIDATION_ERROR') {
		return null;
	}

	const fieldError = getValidationErrors(payload.details ?? {}).find(
		(item) => getFieldName(item.loc) === field
	);
	if (!fieldError) {
		return null;
	}

	const reason = (VALIDATION_TYPE_MESSAGES[fieldError.type] ?? m.validation_bad_format)();
	return capitalize(reason);
}

function formatRetryAfter(value: unknown): string {
	if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
		return m.retry_after_seconds({ seconds: Math.ceil(value) });
	}

	return m.retry_later();
}

function getAccessDeniedMessage(details: ApiErrorDetails): string {
	switch (details.reason) {
		case 'VOTING_TICKET_REQUIRED':
			return m.error_voting_needs_ticket();
		case 'VOTING_DISABLED':
			return m.error_voting_closed();
		case 'MAILING_DELETE_FORBIDDEN':
			return m.error_mailing_not_deletable();
		default:
			return m.error_no_access();
	}
}

function formatColumnList(value: unknown): string {
	if (!Array.isArray(value)) {
		return '';
	}

	return value.filter((column): column is string => typeof column === 'string').join(', ');
}

// The backend rejects a schedule spreadsheet with a `reason` plus whatever
// locates the problem (column, spreadsheet row, duplicated number), so the copy
// can point the organizer at the cell to fix instead of just saying the file is
// wrong. Reasons come from InvalidScheduleFileReason in core/exceptions/schedule.py.
function getInvalidScheduleFileMessage(details: ApiErrorDetails): string {
	const at = m.import_error_location({
		row: String(details.row),
		column: String(details.column)
	});

	switch (details.reason) {
		case 'MISSING_COLUMNS':
			return m.import_error_missing_columns({ columns: formatColumnList(details.columns) });
		case 'EMPTY_FILE':
			return m.import_error_no_events();
		case 'EMPTY_CELL':
			return m.import_error_cell_empty({ at });
		case 'INVALID_NUMBER':
			return m.import_error_integer_required({ at });
		case 'DURATION_NOT_POSITIVE':
			return m.import_error_duration_positive({ at });
		case 'INVALID_TYPE':
			return m.import_error_block_hint({ at });
		case 'BLOCK_ROW_WITH_EVENT_DATA':
			return m.import_error_block_cell({ at });
		case 'DUPLICATE_NUMBER':
			return m.import_error_duplicate_number({
				number: String(details.number),
				row: String(details.row)
			});
		case 'FILE_TOO_LARGE':
			return m.import_error_file_too_large();
		case 'UNSUPPORTED_FILE_TYPE':
			return m.import_error_xlsx_required();
		default:
			return m.import_error_unreadable();
	}
}

// Dictionary: error code -> user-facing message. `satisfies` keeps the literal
// keys (so the drift guard below can see which codes are covered) while checking
// every key is a real ApiErrorCode — a typo'd code is a compile error.
const ERROR_MESSAGES = {
	ALREADY_VOTED_IN_THIS_NOMINATION: m.error_already_voted_in_this_nomination,
	CANNOT_AWARD_SELF: m.error_cannot_award_self,
	CANNOT_CHANGE_OWN_ACCESS: m.error_cannot_change_own_access,
	CANNOT_REMOVE_LAST_SIGN_IN_METHOD: m.error_cannot_remove_last_sign_in_method,
	CAPTCHA_VERIFICATION_FAILED: m.error_captcha_verification_failed,
	CURRENT_EVENT_NOT_ALLOWED: m.error_current_event_not_allowed,
	EMAIL_ALREADY_EXISTS: m.error_email_already_exists,
	EMAIL_DELIVERY_FAILED: m.error_email_delivery_failed,
	EVENT_NOT_FOUND: m.error_event_not_found,
	INCORRECT_PASSWORD: m.error_incorrect_password,
	INVALID_CREDENTIALS: m.error_invalid_credentials,
	INVALID_EMAIL: m.error_invalid_email,
	INVALID_FESTIVAL_TIME_RANGE: m.error_invalid_festival_time_range,
	INVALID_OTP_CODE: m.error_invalid_otp_code,
	INVALID_TELEGRAM_AUTH_PAYLOAD: m.error_invalid_telegram_auth_payload,
	INVALID_VOTING_TIME_RANGE: m.error_invalid_voting_time_range,
	LINK_INITIATOR_MISMATCH: m.error_link_initiator_mismatch,
	MAILING_ALREADY_EXISTS: m.error_mailing_already_exists,
	MAILING_CANCELLED: m.error_mailing_cancelled,
	MAILING_NOT_FOUND: m.error_mailing_not_found,
	OUTDATED_SCHEDULE_CHANGE: m.error_outdated_schedule_change,
	PERMISSION_NOT_ASSIGNABLE: m.error_permission_not_assignable,
	PUSH_SUBSCRIPTION_ALREADY_EXISTS: m.error_push_subscription_already_exists,
	QUEST_AWARD_ALREADY_CANCELLED: m.error_quest_award_already_cancelled,
	QUEST_AWARD_ALREADY_EXISTS: m.error_quest_award_already_exists,
	QUEST_AWARD_AMOUNT_OUT_OF_RANGE: m.error_quest_award_amount_out_of_range,
	QUEST_AWARD_CANCEL_WINDOW_EXPIRED: m.error_quest_award_cancel_window_expired,
	QUEST_AWARD_NOT_FOUND: m.error_quest_award_not_found,
	QUEST_DISABLED: m.error_quest_disabled,
	SAME_EVENTS_ARE_NOT_ALLOWED: m.error_same_events_are_not_allowed,
	SKIPPED_EVENT_NOT_ALLOWED: m.error_skipped_event_not_allowed,
	SOCIAL_ACCOUNT_LINKED_TO_ANOTHER_USER: m.error_social_account_linked_to_another_user,
	SUBSCRIPTION_ALREADY_EXISTS: m.error_subscription_already_exists,
	SYNC_ALREADY_RUNNING: m.error_sync_already_running,
	TICKET_ALREADY_USED: m.error_ticket_already_used,
	TICKET_BARCODE_COLLISION: m.error_ticket_barcode_collision,
	TICKET_NOT_FOUND: m.error_ticket_not_found,
	TICKET_NOT_LINKED: m.error_ticket_not_linked,
	TICKET_REVOKED: m.error_ticket_revoked,
	USER_ALREADY_EXISTS: m.error_user_already_exists,
	USER_ALREADY_HAS_PROVIDER_LINKED: m.error_user_already_has_provider_linked,
	USER_ALREADY_HAS_TICKET_LINKED: m.error_user_already_has_ticket_linked,
	USER_HAS_NO_EMAIL: m.error_user_has_no_email,
	USER_NOT_AUTHENTICATED: m.error_user_not_authenticated,
	USER_NOT_FOUND: m.error_user_not_found,
	USERNAME_ALREADY_TAKEN: m.error_username_already_taken,
	USERNAME_PROFANITY: m.error_username_profanity,
	VOTE_NOT_FOUND: m.error_vote_not_found
} satisfies Partial<Record<ApiErrorCode, () => string>>;

// Codes carrying a `retry_after` detail; all share the same formatted message.
const RETRY_AFTER_CODES = [
	'EMAIL_CODE_REQUEST_TOO_FAST',
	'SCHEDULE_EDIT_TOO_FAST',
	'TEST_NOTIFICATION_TOO_FAST',
	'TOO_MANY_ATTEMPTS',
	'TOO_MANY_OTP_ATTEMPTS',
	'TOO_MANY_LOGIN_ATTEMPTS',
	'TOO_MANY_LOGIN_CODE_REQUESTS'
] as const satisfies readonly ApiErrorCode[];

// Codes intentionally left to the generic fallback toast: not individually
// actionable by the user (server/internal errors) or surfaced by dedicated UI
// elsewhere (not-found states). Listed explicitly so the drift guard passes.
// Underscore-prefixed: consumed only by the type-level guard below, never at
// runtime (matches the `_exhaustiveErrorCodes` convention).
const _GENERIC_FALLBACK_CODES = [
	'AUTHENTICATION_ERROR',
	'HTTP_ERROR',
	'INVALID_PAGE_CURSOR',
	'INTERNAL_ERROR',
	'APP_SETTINGS_NOT_FOUND',
	'NOMINATION_NOT_FOUND',
	'PARTICIPANT_NOT_FOUND',
	'PUSH_SUBSCRIPTION_NOT_FOUND',
	'SCHEDULE_CHANGE_NOT_FOUND',
	'SUBSCRIPTION_NOT_FOUND'
] as const satisfies readonly ApiErrorCode[];

// A network failure rejects `fetch` with a TypeError that each engine words
// differently, so the type is the only stable signal — but a bug in our own
// query code (a property read on undefined) is a TypeError too. So only the ones
// the network produced count, recorded where the call is made.
const connectionFailures = new WeakSet<object>();

function recordConnectionFailure(error: unknown): never {
	if (error instanceof TypeError) {
		connectionFailures.add(error);
	}
	throw error;
}

// Every way the client reads a body. A connection that drops after the headers
// arrived rejects the read with the same TypeError as a failed `fetch`.
const BODY_READS = ['text', 'json', 'arrayBuffer', 'blob', 'formData'] as const;

function recordBodyReadFailures(response: Response): Response {
	for (const method of BODY_READS) {
		const read = response[method].bind(response);
		response[method] = () => {
			// Reading a body twice is a TypeError too, but it is our bug, not the
			// network's. A JSON parse failure is a SyntaxError, so it never counts.
			if (response.bodyUsed) return read();
			return read().catch(recordConnectionFailure);
		};
	}
	return response;
}

// A connection a network blocks without refusing it — a mobile operator's
// whitelist mode, a congested venue cell — can leave a request hanging until the
// OS gives up on TCP, a minute or more, with nothing on screen saying so. The
// deadline turns that hang into a TimeoutError, which the retries, the
// reachability probe and the offline states already treat as no answer. It
// covers the body read too, and is generous enough for an upload on slow Wi-Fi.
const REQUEST_TIMEOUT_MS = 15_000;

/**
 * The `fetch` the generated client calls (`clientConfig.ts`): the real one,
 * bounded by `REQUEST_TIMEOUT_MS` and remembering the TypeErrors the network
 * produces — from `fetch` itself or from reading the body — so
 * `isConnectionFailure` can tell a dropped connection from a bug that happens
 * to throw the same type.
 */
export function fetchRecordingConnectionFailures(
	input: RequestInfo | URL,
	init?: RequestInit
): Promise<Response> {
	// The generated client passes a Request carrying the caller's signal (TanStack
	// Query's, which cancels an unused query); `init.signal` would replace it.
	const callerSignal = input instanceof Request ? input.signal : init?.signal;
	const deadline = timeoutSignal(REQUEST_TIMEOUT_MS);
	const signal = callerSignal ? anySignal([callerSignal, deadline]) : deadline;
	return globalThis
		.fetch(input, { ...init, signal })
		.then(recordBodyReadFailures, recordConnectionFailure);
}

// The generated client never throws: a request that got no response comes back
// as `{ error }` holding what `fetch` or the body read rejected with — a
// TypeError recorded above,
// or a TimeoutError DOMException from `timeoutSignal` or `queryForLoad`. A
// deliberate AbortError is left out: nobody is waiting for that request's answer.
export function isConnectionFailure(error: unknown): boolean {
	if (error instanceof TypeError) {
		return connectionFailures.has(error);
	}
	return error instanceof DOMException && error.name === 'TimeoutError';
}

/**
 * True when a request got no answer from the API itself: the connection
 * failed, timed out, or a proxy answered with its own non-JSON page (a 502
 * from a backend that is down), which the client hands back as a plain string.
 * Worth retrying — unlike an API error body, the server's verdict, or a bug in
 * our own code, which a retry only repeats.
 */
export function gotNoApiAnswer(error: unknown): boolean {
	return isConnectionFailure(error) || typeof error === 'string';
}

/**
 * True for a failed query or mutation that is neither an API error body nor a
 * missing answer — a parse failure or a throw in our own query code. The backend
 * reports its own errors and a dropped connection is expected, so only this is
 * a frontend bug worth reporting. A deliberate cancel or abort is not.
 */
export function isUnexpectedRequestError(error: unknown): boolean {
	if (gotNoApiAnswer(error) || getApiErrorPayload(error) || error instanceof CancelledError) {
		return false;
	}
	return !(error instanceof DOMException && error.name === 'AbortError');
}

/**
 * Russian copy for a failed API call: the mapped `code` of an error response,
 * or the connection message when the request never got an answer. `null` means
 * there is nothing specific to say, so the caller shows its own fallback.
 */
export function getApiErrorDetail(error: unknown): string | null {
	if (isConnectionFailure(error)) {
		return m.error_connection_failed();
	}

	const payload = getApiErrorPayload(error);
	if (!payload) {
		return null;
	}

	// Dictionary covers most codes. Cast because payload.code is an unverified
	// wire string, not a known ApiErrorCode.
	const simple = (ERROR_MESSAGES as Record<string, (() => string) | undefined>)[payload.code];
	if (simple) {
		return simple();
	}

	const details = payload.details ?? {};
	if ((RETRY_AFTER_CODES as readonly string[]).includes(payload.code)) {
		return formatRetryAfter(details.retry_after);
	}
	if (payload.code === 'ACCESS_DENIED') {
		return getAccessDeniedMessage(details);
	}
	if (payload.code === 'INVALID_SCHEDULE_FILE') {
		return getInvalidScheduleFileMessage(details);
	}
	if (payload.code === 'VALIDATION_ERROR') {
		return getValidationMessage(details);
	}
	return null;
}

/**
 * Throw a SvelteKit error from a failed API call, so a `load` failure
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
	const code = getApiErrorPayload(apiError)?.code;
	return kitError(status, message, code ? { code } : {});
}

// Compile-time drift guard: every client-facing code must be covered by the
// dictionary, the retry-after / access-denied / validation handling, or the
// explicit generic-fallback list. If the backend adds a new code that is none of
// these, UnhandledCode stops being `never` and this line fails `pnpm check` —
// naming the missing code(s). Resolve by adding copy to ERROR_MESSAGES or
// listing the code in _GENERIC_FALLBACK_CODES.
type HandledCode =
	| keyof typeof ERROR_MESSAGES
	| (typeof RETRY_AFTER_CODES)[number]
	| (typeof _GENERIC_FALLBACK_CODES)[number]
	| 'ACCESS_DENIED'
	| 'INVALID_SCHEDULE_FILE'
	| 'VALIDATION_ERROR';
type UnhandledCode = Exclude<ApiErrorCode, HandledCode>;

const _exhaustiveErrorCodes: UnhandledCode extends never ? true : UnhandledCode = true;
