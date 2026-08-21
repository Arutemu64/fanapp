import { isReachable, markReachable } from '$lib/services/reachability';
import { isHttpError, error as kitError, redirect } from '@sveltejs/kit';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { loadOnline } from './errors';

describe('loadOnline', () => {
	beforeEach(() => {
		// Reachability is module-global; start every case from the optimistic default.
		markReachable(true);
	});

	it('turns a network rejection into the offline 503 instead of letting it escape', async () => {
		// The bug this guards: openapi-fetch re-throws the raw fetch TypeError, which
		// escaped the load as an unhandled crash and was filed as a Sentry bug.
		const promise = loadOnline(() =>
			Promise.reject(new TypeError('NetworkError when attempting to fetch resource.'))
		);

		await expect(promise).rejects.toSatisfy(
			(thrown: unknown) => isHttpError(thrown) && thrown.status === 503
		);
		expect(isReachable()).toBe(false);
	});

	it('skips the doomed request when the backend is already known unreachable', async () => {
		markReachable(false);
		const run = vi.fn();

		await expect(loadOnline(run)).rejects.toSatisfy(
			(thrown: unknown) => isHttpError(thrown) && thrown.status === 503
		);
		expect(run).not.toHaveBeenCalled();
	});

	it('passes a mapped API error through with its own status', async () => {
		// A server that answered gave a verdict — it must not be reframed as offline.
		await expect(
			loadOnline(() => {
				kitError(403, 'Нет доступа');
			})
		).rejects.toSatisfy((thrown: unknown) => isHttpError(thrown) && thrown.status === 403);
		expect(isReachable()).toBe(true);
	});

	it('passes a redirect through', async () => {
		await expect(
			loadOnline(() => {
				redirect(303, '/login');
			})
		).rejects.toMatchObject({ status: 303, location: '/login' });
	});

	it('returns what the runner produced when the request goes through', async () => {
		await expect(loadOnline(() => Promise.resolve('настройки'))).resolves.toBe('настройки');
		expect(isReachable()).toBe(true);
	});
});
