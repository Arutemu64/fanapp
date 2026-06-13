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
	<!--
		"interaction-only" keeps the widget invisible and auto-solves the managed
		challenge in the background. A visible box only appears if Cloudflare decides
		a real interaction is required, so the normal flow needs no manual solve.
	-->
	<div class="flex justify-center empty:hidden">
		<Turnstile
			{siteKey}
			theme="auto"
			appearance="interaction-only"
			on:callback={(event: CustomEvent<{ token: string }>) => (token = event.detail.token)}
			on:expired={() => (token = null)}
			on:error={() => (token = null)}
			bind:reset
		/>
	</div>
{/if}
