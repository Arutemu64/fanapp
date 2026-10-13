<script lang="ts">
import { PUBLIC_SMARTCAPTCHA_CLIENT_KEY } from '#lib/env.js';

// Captcha is enabled only when a SmartCaptcha client key is configured.
// Without the key the widget renders nothing and the flow works captcha-free,
// which lets us turn the feature off just by leaving the env var empty.
export const captchaEnabled = Boolean(PUBLIC_SMARTCAPTCHA_CLIENT_KEY);
</script>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue';

import { loadSmartCaptcha, type SmartCaptchaApi } from '#lib/utils/smartcaptcha.js';

const emit = defineEmits<{
	/**
	 * Fired once per successful solve, after `token` is set. Lets a caller
	 * resume a submit it parked waiting for the token without watching the
	 * token in a watcher. Not emitted for the expiry/error paths, which only
	 * clear the token.
	 */
	solve: [];
}>();

/** Solved token, or null until the user passes the challenge. */
const token = defineModel<string | null>('token', { default: null });

const container = useTemplateRef<HTMLDivElement>('container');

let api: SmartCaptchaApi | undefined;
let widgetId: number | undefined;
let unmounted = false;
// A submit can arrive before the script finishes loading. Remember that the
// challenge was requested and run it the moment the widget is ready, so a
// slow load doesn't leave the parked submit to time out.
let executeWhenReady = false;

/** Starts the invisible challenge on demand. */
function execute() {
	if (api && widgetId !== undefined) {
		api.execute(widgetId);
	} else {
		executeWhenReady = true;
	}
}

/** Resets the widget to fetch a fresh token. */
function reset() {
	executeWhenReady = false;
	if (api && widgetId !== undefined) {
		api.reset(widgetId);
	}
	token.value = null;
}

// Exposed (not bound through props) so the parent holds callable handles via a
// template ref from the first render, even during the script load window.
defineExpose({ execute, reset });

onMounted(() => {
	const target = container.value;
	// No client key: the container is not rendered (see template), nothing to mount.
	if (!target) {
		return;
	}

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
				// The model update reaches a `v-model:token` parent synchronously
				// (its handler assigns the parent's ref), so a `solve` listener can
				// read the new token straight away.
				callback: (solved) => {
					token.value = solved;
					emit('solve');
				}
			});

			// Expired or errored tokens are unusable — drop them so the caller
			// re-runs execute() on the next submit instead of sending a dead token.
			smartCaptcha.subscribe(widgetId, 'token-expired', () => (token.value = null));
			smartCaptcha.subscribe(widgetId, 'network-error', () => (token.value = null));
			smartCaptcha.subscribe(widgetId, 'javascript-error', () => (token.value = null));

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
});

onBeforeUnmount(() => {
	unmounted = true;
	if (widgetId !== undefined) {
		window.smartCaptcha?.destroy(widgetId);
	}
});
</script>

<template>
	<!--
		Invisible SmartCaptcha renders into this container. It stays empty in the
		common case; a challenge pop-up only appears for suspicious requests.
	-->
	<div v-if="captchaEnabled" ref="container"></div>
</template>
