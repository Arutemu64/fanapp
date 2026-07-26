<script module lang="ts">
	import { PUBLIC_SMARTCAPTCHA_CLIENT_KEY } from '$env/static/public';

	// Captcha is enabled only when a SmartCaptcha client key is configured.
	// Without the key the widget renders nothing and the flow works captcha-free,
	// which lets us turn the feature off just by leaving the env var empty.
	export const captchaEnabled = Boolean(PUBLIC_SMARTCAPTCHA_CLIENT_KEY);
</script>

<script lang="ts">
	import type { Attachment } from 'svelte/attachments';

	import { loadSmartCaptcha, type SmartCaptchaApi } from '$lib/utils/smartcaptcha';

	interface Props {
		/** Solved token, or null until the user passes the challenge. */
		token?: string | null;
		/** Bound to a function that resets the widget to fetch a fresh token. */
		reset?: () => void;
		/** Bound to a function that starts the invisible challenge on demand. */
		execute?: () => void;
		/**
		 * Fired once per successful solve, after `token` is set. Lets a caller
		 * resume a submit it parked waiting for the token without watching the
		 * token in an $effect. Not called for the expiry/error paths, which only
		 * clear the token.
		 */
		onSolve?: () => void;
	}

	let {
		token = $bindable(null),
		reset = $bindable(),
		execute = $bindable(),
		onSolve
	}: Props = $props();

	// An attachment rather than onMount + bind:this: the node arrives non-null, so
	// there is no container state to thread through and no null check, and the
	// teardown sits with the setup that owns it. The {#if} below is what guards on
	// the client key — the attachment only exists when the container renders.
	//
	// Deliberately reads no reactive state while it runs: an attachment re-runs
	// (destroying and re-rendering the widget) whenever state it read during its
	// own run changes. `onSolve` is therefore read lazily, inside the callback.
	const mountSmartCaptcha: Attachment<HTMLDivElement> = (target) => {
		let api: SmartCaptchaApi | undefined;
		let widgetId: number | undefined;
		let unmounted = false;
		// A submit can arrive before the script finishes loading. Remember that the
		// challenge was requested and run it the moment the widget is ready, so a
		// slow load doesn't leave the parked submit to time out.
		let executeWhenReady = false;

		// Assigned synchronously (not after load) so the parent always has callable
		// bindings, even during the load window.
		execute = () => {
			if (api && widgetId !== undefined) {
				api.execute(widgetId);
			} else {
				executeWhenReady = true;
			}
		};
		reset = () => {
			executeWhenReady = false;
			if (api && widgetId !== undefined) {
				api.reset(widgetId);
			}
			token = null;
		};

		loadSmartCaptcha()
			.then((smartCaptcha) => {
				// The component may have unmounted while the script was loading.
				if (unmounted) {
					return;
				}

				api = smartCaptcha;
				widgetId = smartCaptcha.render(target, {
					sitekey: PUBLIC_SMARTCAPTCHA_CLIENT_KEY,
					// Invisible: a token is minted only after execute(), and only
					// suspicious users ever see an actual challenge pop-up.
					invisible: true,
					// `token` is a bindable prop, so the parent sees the new value
					// synchronously — onSolve() can read it straight away. Reading
					// `onSolve` here rather than above also keeps it out of the
					// attachment's dependencies.
					callback: (solved) => {
						token = solved;
						onSolve?.();
					}
				});

				// Expired or errored tokens are unusable — drop them so the caller
				// re-runs execute() on the next submit instead of sending a dead token.
				smartCaptcha.subscribe(widgetId, 'token-expired', () => (token = null));
				smartCaptcha.subscribe(widgetId, 'network-error', () => (token = null));
				smartCaptcha.subscribe(widgetId, 'javascript-error', () => (token = null));

				// Fulfill a challenge that was requested before the widget was ready.
				if (executeWhenReady) {
					executeWhenReady = false;
					smartCaptcha.execute(widgetId);
				}
			})
			.catch((error) => {
				// Script blocked or CDN unreachable: leave token null. The form's
				// captcha gate hits its timeout and surfaces a retryable error.
				console.error('SmartCaptcha failed to load:', error);
			});

		return () => {
			unmounted = true;
			if (widgetId !== undefined) {
				window.smartCaptcha?.destroy(widgetId);
			}
		};
	};
</script>

{#if PUBLIC_SMARTCAPTCHA_CLIENT_KEY}
	<!--
		Invisible SmartCaptcha renders into this container. It stays empty in the
		common case; a challenge pop-up only appears for suspicious requests.
	-->
	<div {@attach mountSmartCaptcha}></div>
{/if}
