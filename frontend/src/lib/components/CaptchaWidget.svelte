<script module lang="ts">
	import { env } from '$env/dynamic/public';

	// Captcha is enabled only when a Turnstile site key is configured.
	// Without the key the widget renders nothing and the flow works captcha-free,
	// which lets us turn the feature off just by leaving the env var empty.
	export const captchaEnabled = Boolean(env.PUBLIC_TURNSTILE_SITE_KEY);
</script>

<script lang="ts">
	import { Turnstile } from 'svelte-turnstile';

	interface Props {
		/** Solved token, or null until the user passes the challenge. */
		token?: string | null;
		/** Bound to a function that resets the widget to fetch a fresh token. */
		reset?: () => void;
	}

	let { token = $bindable(null), reset = $bindable() }: Props = $props();

	const siteKey = env.PUBLIC_TURNSTILE_SITE_KEY;
</script>

{#if siteKey}
	<div class="flex justify-center">
		<Turnstile
			{siteKey}
			theme="auto"
			on:callback={(event: CustomEvent<{ token: string }>) => (token = event.detail.token)}
			on:expired={() => (token = null)}
			on:error={() => (token = null)}
			bind:reset
		/>
	</div>
{/if}
