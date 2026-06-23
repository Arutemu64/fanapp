/// <reference types="unplugin-icons/types/svelte" />

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces

import type { CurrentUserDTO } from '$lib/types/user';

declare global {
	namespace App {
		// SPA-only: there is no server load, so `locals` carries nothing.
		// interface Locals {}
		interface Error {
			message: string;
			code?: string;
		}
		interface PageData {
			user: CurrentUserDTO | null;
			/** Page heading rendered in the navbar; set per page via `load`. */
			title?: string;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
