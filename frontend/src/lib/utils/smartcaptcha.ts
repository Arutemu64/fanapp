// Loads the Yandex SmartCaptcha widget script once and hands callers the ready
// `window.smartCaptcha` API. The script is fetched lazily (only when a captcha
// widget actually mounts) and shared across every widget on the page.

export interface SmartCaptchaRenderParams {
	/** Client-side key from the SmartCaptcha console. */
	sitekey: string;
	/** Invisible mode: a token is produced only after execute(), no checkbox. */
	invisible?: boolean;
	/** Optional callback fired with the token once the user passes. */
	callback?: (token: string) => void;
}

type SmartCaptchaEvent =
	| 'challenge-visible'
	| 'challenge-hidden'
	| 'network-error'
	| 'javascript-error'
	| 'success'
	| 'token-expired';

export interface SmartCaptchaApi {
	render(container: HTMLElement | string, params: SmartCaptchaRenderParams): number;
	execute(widgetId?: number): void;
	reset(widgetId?: number): void;
	destroy(widgetId?: number): void;
	getResponse(widgetId?: number): string;
	subscribe(widgetId: number, event: SmartCaptchaEvent, callback: () => void): () => void;
}

declare global {
	interface Window {
		smartCaptcha?: SmartCaptchaApi;
		// Global callback the SmartCaptcha script invokes once it is ready. Its
		// name must match the `onload=` query parameter in SCRIPT_SRC below.
		onSmartCaptchaLoad?: () => void;
	}
}

// `render=onload` defers rendering to our own render() calls; `onload=` names the
// global callback the script runs when window.smartCaptcha becomes available.
const SCRIPT_SRC =
	'https://smartcaptcha.cloud.yandex.ru/captcha.js?render=onload&onload=onSmartCaptchaLoad';

let readyPromise: Promise<SmartCaptchaApi> | undefined;

export function loadSmartCaptcha(): Promise<SmartCaptchaApi> {
	// Already loaded (e.g. a second widget mounted after the first).
	if (window.smartCaptcha) {
		return Promise.resolve(window.smartCaptcha);
	}
	// Load in flight — share the same promise so the script is injected once.
	if (readyPromise) {
		return readyPromise;
	}

	readyPromise = new Promise<SmartCaptchaApi>((resolve, reject) => {
		window.onSmartCaptchaLoad = () => {
			if (window.smartCaptcha) {
				resolve(window.smartCaptcha);
			} else {
				reject(new Error('SmartCaptcha script loaded without window.smartCaptcha'));
			}
		};

		const script = document.createElement('script');
		script.src = SCRIPT_SRC;
		script.async = true;
		script.onerror = () => {
			// A failed load can't be retried on the same promise, so clear it to let
			// a later widget mount try again.
			readyPromise = undefined;
			reject(new Error('Failed to load the SmartCaptcha script'));
		};
		document.head.appendChild(script);
	});

	return readyPromise;
}
