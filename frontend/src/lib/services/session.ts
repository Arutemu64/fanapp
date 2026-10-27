import type { QueryClient } from '@tanstack/svelte-query';

import { createContext } from 'svelte';

import { dropQueuedWrites } from '#lib/api/writeQueue.js';
import { timeoutSignal } from '#lib/utils/fetchTimeout.js';

import {
	clearLogoutPending,
	currentUserOptions,
	flushPendingLogout,
	isLogoutPending,
	markLogoutPending
} from './identity.js';

const SETTLE_LOGOUT_TIMEOUT_MS = 8000;

export interface SessionRouter {
	goToLoginTarget: () => Promise<void>;
	goHome: () => Promise<void>;
	redirectToLogin: () => Promise<void>;
}

interface SessionDeps {
	queryClient: QueryClient;
	events: { restart: () => void };
	router: SessionRouter;
	isReachable: () => boolean;
	unsubscribePush: () => Promise<void>;
}

const [getSession, setSessionContext] = createContext<Session>();

export class Session {
	readonly #queryClient: QueryClient;
	readonly #events: SessionDeps['events'];
	readonly #router: SessionRouter;
	readonly #isReachable: () => boolean;
	readonly #unsubscribePush: () => Promise<void>;

	constructor(deps: SessionDeps) {
		this.#queryClient = deps.queryClient;
		this.#events = deps.events;
		this.#router = deps.router;
		this.#isReachable = deps.isReachable;
		this.#unsubscribePush = deps.unsubscribePush;
	}

	async loggedIn(): Promise<void> {
		clearLogoutPending();

		void this.#queryClient.invalidateQueries();
		await this.#queryClient.refetchQueries(
			{ queryKey: currentUserOptions().queryKey },
			{ cancelRefetch: false }
		);

		await this.#router.goToLoginTarget();
		this.#events.restart();
	}

	async logOut(revokeOnServer: () => Promise<unknown>): Promise<void> {
		if (this.#isReachable()) {
			await revokeOnServer();
		} else {
			markLogoutPending();
		}

		this.#queryClient.setQueryData(currentUserOptions().queryKey, null);
		await this.#router.goHome();
		await this.#forgetAccount();
	}

	get logoutPending(): boolean {
		return isLogoutPending();
	}

	async settlePendingLogout(): Promise<boolean> {
		await flushPendingLogout(timeoutSignal(SETTLE_LOGOUT_TIMEOUT_MS));
		return !isLogoutPending();
	}

	async expired(): Promise<void> {
		const { queryKey } = currentUserOptions();
		if (!this.#queryClient.getQueryData(queryKey)) return;
		this.#queryClient.setQueryData(queryKey, null);

		await this.#router.redirectToLogin();
		await this.#forgetAccount();
	}

	async #forgetAccount(): Promise<void> {
		this.#queryClient.removeQueries({ type: 'inactive' });
		dropQueuedWrites(this.#queryClient);
		void this.#queryClient.invalidateQueries();
		this.#events.restart();
		await this.#unsubscribePush();
	}
}

export function setSession(deps: SessionDeps): Session {
	const session = new Session(deps);
	setSessionContext(session);
	return session;
}

export { getSession };
