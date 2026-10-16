/// <reference types="unplugin-icons/types/svelte" />

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces

import type { BackTarget, NavbarAction } from '#lib/types/navigation.js';

declare global {
	namespace App {
		// SPA-only: there is no server load, so `locals` carries nothing.
		// interface Locals {}
		interface Error {
			message: string;
			code?: string;
			/** Reference for a reported unexpected error; set by handleError in hooks.client.ts. */
			errorId?: string;
		}
		interface PageData {
			/** Page heading rendered in the navbar; set per page via `load`. */
			title?: string;
			/** Parent route for the navbar's back arrow; set by nested pages via `load`. */
			back?: BackTarget;
			/** Icon buttons beside the bell; set per page via `load` (universal, so it can carry a component). */
			actions?: NavbarAction[];
		}
		interface PageState {
			/** The login page's current step; absent means the options screen. */
			loginStep?: 'email' | 'password' | 'code';
			/** The address the login code went to; set alongside `loginStep: 'code'`. */
			loginCodeEmail?: string;
		}
		// interface Platform {}
	}

	/** Release number from backend/pyproject.toml; empty when the build had none. Set by vite.config.ts `define`. */
	const __APP_VERSION__: string;
	/** Commit SHA of the build; empty when the build had none. Set by vite.config.ts `define`. */
	const __APP_BUILD__: string;
}

export {};
