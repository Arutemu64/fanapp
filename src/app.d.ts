// See https://svelte.dev/docs/kit/types#app.d.ts

import type { FullUserDTO } from '$lib/types/user';

// for information about these interfaces
declare global {
	namespace App {
		interface Locals {
			user: FullUserDTO | null;
		}
		// interface Error {}
		interface PageData {
			user: FullUserDTO | null;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
