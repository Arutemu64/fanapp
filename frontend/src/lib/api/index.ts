import {
	CancelledError,
	type QueryClient,
	type QueryExecuteOptions,
	type QueryKey
} from '@tanstack/svelte-query';

import type { ResolvedRequestOptions } from '#lib/api/generated/client/index.js';

import { getApiErrorCode, gotNoApiAnswer } from '#lib/api/errors.js';
import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { client } from '#lib/api/generated/client.gen.js';
import {
	isBackendUnreachableStatus,
	markReachable,
	probeReachability
} from '#lib/services/reachability.js';
import { FIRST_PAINT_TIMEOUT_MS } from '#lib/utils/fetchTimeout.js';

export function queryForLoad<TData, TError, TQueryKey extends QueryKey>(
	queryClient: QueryClient,
	options: QueryExecuteOptions<TData, TError, TData, TData, TQueryKey>
): Promise<TData> {
	let timer: ReturnType<typeof setTimeout> | undefined;
	const budget = new Promise<never>((_, reject) => {
		timer = setTimeout(
			() => reject(new DOMException('signal timed out', 'TimeoutError')),
			FIRST_PAINT_TIMEOUT_MS
		);
	});
	const query = queryClient.query({ ...options, retry: false, networkMode: 'always' });
	return Promise.race([query, budget]).finally(() => clearTimeout(timer));
}

const IDENTITY_PATH = '/me';
const CREDENTIAL_CHECK_PATHS = new Set(['/auth/login', '/auth/login-with-code']);

const SESSION_ERROR_CODES = new Set(['AUTHENTICATION_ERROR', 'USER_NOT_AUTHENTICATED']);

export function watchBackgroundRefetchErrors(
	queryClient: QueryClient,
	onFailure: () => void
): () => void {
	return queryClient.getQueryCache().subscribe((event) => {
		if (event.type !== 'updated' || event.action.type !== 'error') return;

		const { query } = event;
		const error: unknown = event.action.error;
		if (query.state.data === undefined || query.getObserversCount() === 0) return;
		if (query.state.fetchMeta?.fetchMore) return;
		if (query.meta?.quietRefetchErrors === true) return;
		if (gotNoApiAnswer(error) || error instanceof CancelledError) return;
		if (SESSION_ERROR_CODES.has(getApiErrorCode(error) ?? '')) return;

		onFailure();
	});
}

export function watchApiResponses(
	queryClient: QueryClient,
	onSessionExpired: () => void
): () => void {
	const responseId = client.interceptors.response.use(
		(response: Response, _request: Request, options: ResolvedRequestOptions) => {
			markReachable(!isBackendUnreachableStatus(response.status));

			if (response.status !== 401) return response;
			if (CREDENTIAL_CHECK_PATHS.has(options.url)) return response;
			if (options.url === IDENTITY_PATH) {
				onSessionExpired();
			} else {
				void queryClient.refetchQueries(
					{ queryKey: getCurrentUserQueryKey() },
					{ cancelRefetch: false }
				);
			}
			return response;
		}
	);

	const errorId = client.interceptors.error.use((error: unknown, response?: Response) => {
		if (!response) {
			void probeReachability();
		}
		return error;
	});

	return () => {
		client.interceptors.response.eject(responseId);
		client.interceptors.error.eject(errorId);
	};
}
