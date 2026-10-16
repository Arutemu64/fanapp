import type { QueryClient } from '@tanstack/svelte-query';

import { createContext } from 'svelte';

import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { currentUserOptions } from '#lib/api/index.js';
import { timeoutSignal } from '#lib/utils/fetchTimeout.js';
import {
	clearLogoutPending,
	flushPendingLogout,
	isLogoutPending,
	markLogoutPending
} from '#lib/utils/pendingLogout.js';

// The user is waiting on the provider button, so a stalled revoke must give up
// and let them retry instead of spinning until the browser's own TCP timeout.
const SETTLE_LOGOUT_TIMEOUT_MS = 8000;

/** The navigation a session change needs, so the module is testable without a router. */
export interface SessionRouter {
	/** Where a fresh login lands: the validated `?next=` target, home otherwise. */
	goToLoginTarget(): Promise<void>;
	goHome(): Promise<void>;
	/**
	 * Send the open screen to `/login`, remembering it as `?next=`, if it sits
	 * behind the `(protected)` guard. The guard only runs on navigation, so a
	 * screen already open has to be left explicitly. A no-op elsewhere.
	 */
	redirectToLogin(): Promise<void>;
}

interface SessionDeps {
	queryClient: QueryClient;
	/** The live event stream is bound to one identity, so it redials on every change. */
	events: { restart(): void };
	router: SessionRouter;
	isReachable: () => boolean;
	/** Ends this device's push subscription; never throws. */
	unsubscribePush: () => Promise<void>;
}

const [getSession, setSessionContext] = createContext<Session>();

/**
 * Every identity transition and its side effects, in one place: callers say
 * "logged in", "log out" or "expired" and never repeat the step list.
 *
 * Cache, pending logout and event stream all belong to whoever is signed in, so
 * they must change together: a transition that skips one leaves the previous
 * user's data or live stream on screen for the next visitor.
 */
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

	/**
	 * A login form succeeded: load the new identity and move on. Shared by every
	 * form that doesn't leave the page (a social login returns as a full page load).
	 */
	async loggedIn(): Promise<void> {
		// A logout queued while offline must not outlive a deliberate re-login: clear
		// it so the reconnect flush can't revoke this fresh session (see pendingLogout).
		clearLogoutPending();

		// Everything cached so far was fetched as a guest: mark it all stale, so what
		// is on screen refetches now and the rest when next shown. Identity is awaited,
		// since the guards on the way to `next` read it from the cache; it joins the
		// /me/ refetch the invalidation just started instead of aborting it.
		void this.#queryClient.invalidateQueries();
		await this.#queryClient.refetchQueries(
			{ queryKey: getCurrentUserQueryKey() },
			{ cancelRefetch: false }
		);

		await this.#router.goToLoginTarget();
		this.#events.restart();
	}

	/**
	 * The user chose to leave. `revokeOnServer` ends the session server-side and
	 * may throw, which aborts the logout so the caller can report it; the caller
	 * owns the request (and its busy state), the session owns what follows.
	 *
	 * Offline there is no server to ask and the HttpOnly cookie can't be cleared
	 * from JS, so the intent is recorded instead (see pendingLogout) and local
	 * state is torn down now, so a shared device stops showing this account.
	 */
	async logOut(revokeOnServer: () => Promise<unknown>): Promise<void> {
		if (this.#isReachable()) {
			await revokeOnServer();
		} else {
			markLogoutPending();
		}

		// Guest from here on: the user query turns null at once (the bell and every
		// account row drop), then, once home has replaced the screen, the account's
		// cached data is forgotten.
		this.#queryClient.setQueryData(currentUserOptions().queryKey, null);
		await this.#router.goHome();
		await this.#forgetAccount();
	}

	/** True while a logout made offline still waits for its server revoke. */
	get logoutPending(): boolean {
		return isLogoutPending();
	}

	/**
	 * Call before leaving for an OAuth provider while `logoutPending`. A social
	 * login returns as a full page load, whose boot flush would send the queued
	 * revoke with the *new* session's cookie and end it. Clearing the intent
	 * instead is wrong too: an abandoned OAuth flow would then let the still-valid
	 * old cookie restore the account the user left. So revoke the old session now.
	 * Resolves `false` when that couldn't be confirmed in time, and the caller
	 * stays put; the intent is kept, so a retry or the next reconnect sends it.
	 */
	async settlePendingLogout(): Promise<boolean> {
		await flushPendingLogout(timeoutSignal(SETTLE_LOGOUT_TIMEOUT_MS));
		return !isLogoutPending();
	}

	/** The server said the session is gone (a 401 from `/me/`), whatever the screen. */
	async expired(): Promise<void> {
		const { queryKey } = currentUserOptions();
		// A guest was already a guest; this also makes a burst of 401s end it once.
		if (!this.#queryClient.getQueryData(queryKey)) return;
		this.#queryClient.setQueryData(queryKey, null);

		await this.#router.redirectToLogin();
		await this.#forgetAccount();
	}

	/**
	 * Drop what the previous account left behind once the app shows the guest
	 * state. Queries no screen is using are removed, so the persisted cache stops
	 * holding them for the next person on a shared device; the ones on screen
	 * refetch as the guest. The event stream redials as the guest too — otherwise
	 * it keeps delivering the previous user's `notification_created` events. The
	 * push subscription ends for the same reason: the server ties it to this
	 * account, so the next person would get its pushes on the lock screen.
	 */
	async #forgetAccount(): Promise<void> {
		this.#queryClient.removeQueries({ type: 'inactive' });
		void this.#queryClient.invalidateQueries();
		this.#events.restart();
		// Last, so a slow browser call can't hold up the rest of the teardown, but
		// awaited, so the transition ends only once the subscription is gone and a
		// login that switches push back on can't have its new one dropped by this.
		await this.#unsubscribePush();
	}
}

/** Create the session and put it in Svelte context (call in the root layout). */
export function setSession(deps: SessionDeps): Session {
	const session = new Session(deps);
	setSessionContext(session);
	return session;
}

export { getSession };
