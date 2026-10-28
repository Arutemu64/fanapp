import { error as kitError } from '@sveltejs/kit';
import { CancelledError } from '@tanstack/svelte-query';

import type {
	InvalidScheduleFileProblem,
	InvalidScheduleFileReason,
	ProblemDetails
} from '#lib/api/generated/index.js';

import { m } from '#lib/paraglide/messages.js';
import { anySignal, timeoutSignal } from '#lib/utils/fetchTimeout.js';

type ApiErrorCode = ProblemDetails['code'];

type ApiProblem = Record<string, unknown> & { code: string };

type ValidationContext = Record<string, unknown>;

interface ApiValidationErrorDetail {
	loc: (string | number)[];
	type: string;
	ctx?: ValidationContext;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return Boolean(value) && typeof value === 'object';
}

function getApiProblem(error: unknown): ApiProblem | null {
	if (!isRecord(error) || typeof error.code !== 'string') {
		return null;
	}

	return { ...error, code: error.code };
}

function getValidationErrors(problem: ApiProblem): ApiValidationErrorDetail[] {
	const rawErrors = problem.errors;
	if (!Array.isArray(rawErrors)) {
		return [];
	}

	return rawErrors.filter(
		(item): item is ApiValidationErrorDetail =>
			isRecord(item) && Array.isArray(item.loc) && typeof item.type === 'string'
	);
}

function getFieldName(path: (string | number)[]): string | null {
	const [location, ...rest] = path;
	const isLocation = typeof location === 'string' && ['body', 'query', 'path'].includes(location);
	const fieldPath = isLocation ? rest : path;

	const lastSegment = fieldPath
		.filter((segment): segment is string => typeof segment === 'string')
		.at(-1);

	return lastSegment ?? null;
}

function getFieldLabel(path: (string | number)[]): string | null {
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

function uncapitalize(text: string): string {
	return text.charAt(0).toLowerCase() + text.slice(1);
}

function tooShortReason(ctx: ValidationContext): string {
	if (typeof ctx.min_length === 'number') {
		return uncapitalize(m.validation_min_chars({ count: ctx.min_length }));
	}
	return m.validation_too_short();
}

function tooLongReason(ctx: ValidationContext): string {
	if (typeof ctx.max_length === 'number') {
		return uncapitalize(m.validation_max_chars({ count: ctx.max_length }));
	}
	return m.validation_too_long();
}

const VALIDATION_TYPE_MESSAGES: Record<string, (ctx: ValidationContext) => string> = {
	missing: m.validation_missing,
	string_too_short: tooShortReason,
	string_too_long: tooLongReason,
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

function getValidationMessage(problem: ApiProblem): string {
	const firstError = getValidationErrors(problem)[0];
	if (!firstError) {
		return m.validation_check_form();
	}

	const fieldLabel = getFieldLabel(firstError.loc);
	const reason = VALIDATION_TYPE_MESSAGES[firstError.type]?.(firstError.ctx ?? {});

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

export function getApiErrorCode(error: unknown): string | undefined {
	return getApiProblem(error)?.code;
}

export function getApiFieldError(error: unknown, field: string): string | null {
	const problem = getApiProblem(error);
	if (problem?.code !== 'VALIDATION_ERROR') {
		return null;
	}

	const fieldError = getValidationErrors(problem).find((item) => getFieldName(item.loc) === field);
	if (!fieldError) {
		return null;
	}

	const reason = (VALIDATION_TYPE_MESSAGES[fieldError.type] ?? m.validation_bad_format)(
		fieldError.ctx ?? {}
	);
	return capitalize(reason);
}

function formatRetryAfter(value: unknown): string {
	if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
		return m.retry_after_seconds({ seconds: Math.ceil(value) });
	}

	return m.retry_later();
}

function formatColumnList(value: unknown): string {
	if (!Array.isArray(value)) {
		return '';
	}

	return value.filter((column): column is string => typeof column === 'string').join(', ');
}

type ScheduleFileMessage = (problem: Partial<InvalidScheduleFileProblem>, at: string) => string;

const SCHEDULE_FILE_MESSAGES = {
	unreadable_file: () => m.import_error_unreadable(),
	missing_columns: (problem) =>
		m.import_error_missing_columns({ columns: formatColumnList(problem.columns) }),
	empty_file: () => m.import_error_no_events(),
	empty_cell: (_problem, at) => m.import_error_cell_empty({ at }),
	invalid_number: (_problem, at) => m.import_error_integer_required({ at }),
	duration_not_positive: (_problem, at) => m.import_error_duration_positive({ at }),
	invalid_type: (_problem, at) => m.import_error_block_hint({ at }),
	block_row_with_event_data: (_problem, at) => m.import_error_block_cell({ at }),
	duplicate_number: (problem) =>
		m.import_error_duplicate_number({
			number: String(problem.number),
			row: String(problem.row)
		}),
	file_too_large: () => m.import_error_file_too_large(),
	unsupported_file_type: () => m.import_error_xlsx_required()
} satisfies Record<InvalidScheduleFileReason, ScheduleFileMessage>;

function getInvalidScheduleFileMessage(problem: ApiProblem): string {
	const fields = problem as Partial<InvalidScheduleFileProblem>;
	const at = m.import_error_location({
		row: String(fields.row),
		column: String(fields.column)
	});

	const message = (SCHEDULE_FILE_MESSAGES as Record<string, ScheduleFileMessage | undefined>)[
		String(fields.reason)
	];
	if (!message) {
		return m.import_error_unreadable();
	}
	return message(fields, at);
}

const ERROR_MESSAGES = {
	ACCESS_DENIED: m.error_no_access,
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
	INVALID_TCLOUD_EVENT_ID: m.error_invalid_tcloud_event_id,
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
	SOCIAL_ACCOUNT_NOT_LINKED: m.error_social_account_not_linked,
	SUBSCRIPTION_ALREADY_EXISTS: m.error_subscription_already_exists,
	SYNC_ALREADY_RUNNING: m.error_sync_already_running,
	TELEGRAM_BOT_BLOCKED: m.error_telegram_bot_blocked,
	TICKET_ALREADY_USED: m.error_ticket_already_used,
	TICKET_BATCH_ALREADY_EXISTS: m.error_ticket_batch_already_exists,
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
	VK_MESSAGES_NOT_ALLOWED: m.vk_messages_not_allowed,
	VOTE_NOT_FOUND: m.error_vote_not_found,
	VOTING_DISABLED: m.error_voting_closed,
	VOTING_TICKET_REQUIRED: m.error_voting_needs_ticket
} satisfies Partial<Record<ApiErrorCode, () => string>>;

const RETRY_AFTER_CODES = [
	'EMAIL_CODE_REQUEST_TOO_FAST',
	'SCHEDULE_EDIT_TOO_FAST',
	'TEST_NOTIFICATION_TOO_FAST',
	'TOO_MANY_ATTEMPTS',
	'TOO_MANY_OTP_ATTEMPTS',
	'TOO_MANY_LOGIN_ATTEMPTS',
	'TOO_MANY_LOGIN_CODE_REQUESTS',
	'NOTIFICATIONS_CHECK_TOO_FAST'
] as const satisfies readonly ApiErrorCode[];

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

const connectionFailures = new WeakSet<object>();

function recordConnectionFailure(error: unknown): never {
	if (error instanceof TypeError) {
		connectionFailures.add(error);
	}
	throw error;
}

const BODY_READS = ['text', 'json', 'arrayBuffer', 'blob', 'formData'] as const;

function recordBodyReadFailures(response: Response): Response {
	for (const method of BODY_READS) {
		const read = response[method].bind(response);
		response[method] = () => {
			if (response.bodyUsed) return read();
			return read().catch(recordConnectionFailure);
		};
	}
	return response;
}

const REQUEST_TIMEOUT_MS = 15_000;

export function fetchRecordingConnectionFailures(
	input: RequestInfo | URL,
	init?: RequestInit
): Promise<Response> {
	const callerSignal = input instanceof Request ? input.signal : init?.signal;
	const deadline = timeoutSignal(REQUEST_TIMEOUT_MS);
	const signal = callerSignal ? anySignal([callerSignal, deadline]) : deadline;
	return globalThis
		.fetch(input, { ...init, signal })
		.then(recordBodyReadFailures, recordConnectionFailure);
}

export function isConnectionFailure(error: unknown): boolean {
	if (error instanceof TypeError) {
		return connectionFailures.has(error);
	}
	return error instanceof DOMException && error.name === 'TimeoutError';
}

export function gotNoApiAnswer(error: unknown): boolean {
	return isConnectionFailure(error) || typeof error === 'string';
}

export function isUnexpectedRequestError(error: unknown): boolean {
	if (gotNoApiAnswer(error) || getApiProblem(error) || error instanceof CancelledError) {
		return false;
	}
	return !(error instanceof DOMException && error.name === 'AbortError');
}

export function getApiErrorDetail(error: unknown): string | null {
	if (isConnectionFailure(error)) {
		return m.error_connection_failed();
	}

	const problem = getApiProblem(error);
	if (!problem) {
		return null;
	}

	const simple = (ERROR_MESSAGES as Record<string, (() => string) | undefined>)[problem.code];
	if (simple) {
		return simple();
	}

	if ((RETRY_AFTER_CODES as readonly string[]).includes(problem.code)) {
		return formatRetryAfter(problem.retry_after);
	}
	if (problem.code === 'INVALID_SCHEDULE_FILE') {
		return getInvalidScheduleFileMessage(problem);
	}
	if (problem.code === 'VALIDATION_ERROR') {
		return getValidationMessage(problem);
	}
	return null;
}

export function throwApiError(apiError: unknown, fallback: string): never {
	const message = getApiErrorDetail(apiError) ?? fallback;
	const problem = getApiProblem(apiError);
	return kitError(problemStatus(problem), message, problem ? { code: problem.code } : {});
}

function problemStatus(problem: ApiProblem | null): number {
	const status = problem?.status;
	if (typeof status === 'number' && status >= 400 && status <= 599) {
		return status;
	}
	return 500;
}

type HandledCode =
	| keyof typeof ERROR_MESSAGES
	| (typeof RETRY_AFTER_CODES)[number]
	| (typeof _GENERIC_FALLBACK_CODES)[number]
	| 'INVALID_SCHEDULE_FILE'
	| 'VALIDATION_ERROR';
type UnhandledCode = Exclude<ApiErrorCode, HandledCode>;

const _exhaustiveErrorCodes: UnhandledCode extends never ? true : UnhandledCode = true;
