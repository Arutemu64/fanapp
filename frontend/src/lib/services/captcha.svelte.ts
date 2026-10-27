import { type Challenge, solveChallengeWorkers } from 'altcha/lib';
import Pbkdf2Worker from 'altcha/workers/pbkdf2?worker';

import { getCaptchaChallenge } from '#lib/api/generated/sdk.gen.js';

const CAPTCHA_TIMEOUT_MS = 20_000;
const EXPIRY_MARGIN_MS = 30_000;

export class CaptchaFailedError extends Error {}

interface Solved {
	token: string | null;
	expiresAt: number | null;
}

export class Captcha {
	solving = $state(false);

	#pending: Promise<Solved> | undefined;
	#controller: AbortController | undefined;
	#disposed = false;

	prefetch(): void {
		if (this.#disposed || this.#pending) {
			return;
		}
		const pending = this.#solve();
		pending.catch(() => {});
		this.#pending = pending;
	}

	async take(): Promise<string | null> {
		const pending = this.#pending ?? this.#solve();
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

	dispose(): void {
		this.#disposed = true;
		this.#controller?.abort();
		this.#pending = undefined;
	}

	async #solve(): Promise<Solved> {
		const controller = new AbortController();
		this.#controller = controller;
		const timer = setTimeout(() => controller.abort(), CAPTCHA_TIMEOUT_MS);
		try {
			const { data, error } = await getCaptchaChallenge({ signal: controller.signal });
			if (data === undefined) {
				// eslint-disable-next-line @typescript-eslint/only-throw-error -- the API error body is a plain object
				throw error;
			}
			if (data.challenge === null) {
				return { token: null, expiresAt: null };
			}

			const challenge = data.challenge as unknown as Challenge;
			const solution = await solveChallengeWorkers({
				challenge,
				concurrency: navigator.hardwareConcurrency || 2,
				createWorker: () => new Pbkdf2Worker(),
				controller
			});
			if (solution === null) {
				throw new CaptchaFailedError('Captcha solve timed out or was aborted');
			}

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
