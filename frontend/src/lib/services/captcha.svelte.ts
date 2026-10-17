import { type Challenge, solveChallengeWorkers } from 'altcha/lib';
import Pbkdf2Worker from 'altcha/workers/pbkdf2?worker';

import { getCaptchaChallenge } from '#lib/api/generated/sdk.gen.js';

// One budget for fetching the challenge and solving it. The API sets a difficulty
// a phone at the venue clears in a second or two; this only catches a dead
// network or a device far slower than that.
const CAPTCHA_TIMEOUT_MS = 20_000;
// A pre-solved token this close to its expiry would die on the way to the API,
// so solve a fresh one instead.
const EXPIRY_MARGIN_MS = 30_000;

// The fetch failed, the solve timed out, or the captcha was disposed mid-solve.
export class CaptchaFailedError extends Error {}

interface Solved {
	/** Single-use proof for `captcha_token`; null when the API has captcha off. */
	token: string | null;
	/** Epoch milliseconds, or null for a challenge that never expires. */
	expiresAt: number | null;
}

/**
 * ALTCHA proof-of-work for the login-code request, solved in Web Workers with no
 * UI (ADR-0037).
 * Instantiate one per form: `prefetch()` on mount solves in the background so a
 * token is usually ready by submit, and `take()` hands one out exactly once.
 */
export class Captcha {
	// True while a submit waits on take(), so the form can show it as sending.
	solving = $state(false);

	#pending: Promise<Solved> | undefined;
	#controller: AbortController | undefined;

	prefetch(): void {
		if (this.#pending) {
			return;
		}
		const pending = this.#solve();
		// A prefetch nobody takes must not surface as an unhandled rejection;
		// take() still sees the failure when it awaits the same promise.
		pending.catch(() => {});
		this.#pending = pending;
	}

	/**
	 * A fresh token for `captcha_token` (null when captcha is off). Throws
	 * CaptchaFailedError when no token could be produced.
	 */
	async take(): Promise<string | null> {
		const pending = this.#pending ?? this.#solve();
		// Tokens are single-use: whatever happens next, the next take() solves anew.
		this.#pending = undefined;
		this.solving = true;
		try {
			let solved = await pending;
			if (solved.expiresAt !== null && Date.now() > solved.expiresAt - EXPIRY_MARGIN_MS) {
				solved = await this.#solve();
			}
			return solved.token;
		} finally {
			this.solving = false;
		}
	}

	// Stop the workers when the form unmounts mid-solve.
	dispose(): void {
		this.#controller?.abort();
		this.#pending = undefined;
	}

	async #solve(): Promise<Solved> {
		const controller = new AbortController();
		this.#controller = controller;
		const timer = setTimeout(() => controller.abort(), CAPTCHA_TIMEOUT_MS);
		try {
			const { data } = await getCaptchaChallenge({ signal: controller.signal });
			if (data === undefined) {
				throw new CaptchaFailedError('Captcha challenge request failed');
			}
			if (data.challenge === null) {
				return { token: null, expiresAt: null };
			}

			// The API passes the challenge through untyped so the signed JSON reaches
			// the solver unchanged; its shape is ALTCHA's own Challenge.
			const challenge = data.challenge as unknown as Challenge;
			const solution = await solveChallengeWorkers({
				challenge,
				concurrency: navigator.hardwareConcurrency || 2,
				// Only the PBKDF2 worker ships: the API issues nothing else, and an
				// unexpected algorithm fails the solve loudly rather than hanging.
				createWorker: () => new Pbkdf2Worker(),
				controller
			});
			if (solution === null) {
				throw new CaptchaFailedError('Captcha solve timed out or was aborted');
			}

			// The payload the ALTCHA widget would submit: base64 JSON of the challenge
			// (without codeChallenge) and its solution.
			const token = btoa(
				JSON.stringify({
					challenge: { parameters: challenge.parameters, signature: challenge.signature },
					solution
				})
			);
			const expiresAtSeconds = challenge.parameters.expiresAt;
			const expiresAt = expiresAtSeconds === undefined ? null : expiresAtSeconds * 1000;
			return { token, expiresAt };
		} finally {
			clearTimeout(timer);
		}
	}
}
