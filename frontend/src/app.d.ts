/// <reference types="unplugin-icons/types/svelte" />

import type { BackTarget, NavbarAction } from '#lib/types/navigation.js';

declare global {
	namespace App {
		interface Error {
			message: string;
			code?: string;
			errorId?: string;
		}
		interface PageData {
			title?: string;
			back?: BackTarget;
			actions?: NavbarAction[];
		}
		interface PageState {
			loginStep?: 'email' | 'password' | 'code';
			loginCodeEmail?: string;
		}
	}

	const __APP_VERSION__: string;
	const __APP_BUILD__: string;
}

export {};
