<!--
@component
Yandex SmartCaptcha in invisible mode. Yandex rather than Turnstile because
Cloudflare is frequently throttled in Russia.

Renders nothing unless `PUBLIC_SMARTCAPTCHA_CLIENT_KEY` is set, so callers
must gate their submit path on the exported `captchaEnabled` flag rather than
waiting on a token that will never arrive.

Invisible mode mints a token only after `execute()`: bind `execute` and call
it when submitting, pass the bound `token` to the API, then call the bound
`reset` to fetch a fresh single-use token for the next request.
-->
<script module lang="ts">
	import { PUBLIC_SMARTCAPTCHA_CLIENT_KEY } from '$env/static/public';

	// Captcha is enabled only when a SmartCaptcha client key is configured.
	// Without the key the widget renders nothing and the flow works captcha-free,
	// which lets us turn the feature off just by leaving the env var empty.
	export const captchaEnabled = Boolean(PUBLIC_SMARTCAPTCHA_CLIENT_KEY);
</script>

<script lang="ts">
	import { loadSmartCaptcha, type SmartCaptchaApi } from '$lib/utils/smartcaptcha';
	import { onMount } from 'svelte';

	interface Props {
		/** Solved token, or null until the user passes the challenge. */
		token?: string | null;
		/** Bound to a function that resets the widget to fetch a fresh token. */
		reset?: () => void;
		/** Bound to a function that starts the invisible challenge on demand. */
		execute?: () => void;
	}

	let { token = $bindable(null), reset = $bindable(), execute = $bindable() }: Props = $props();

	let container = $state<HTMLDivElement>();

	onMount(() => {
		if (!PUBLIC_SMARTCAPTCHA_CLIENT_KEY || !container) {
			return;
		}

		const target = container;

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
					callback: (solved) => (token = solved)
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
	});
</script>

{#if PUBLIC_SMARTCAPTCHA_CLIENT_KEY}
	<!--
		Invisible SmartCaptcha renders into this container. It stays empty in the
		common case; a challenge pop-up only appears for suspicious requests.
	-->
	<div bind:this={container}></div>
{/if}
