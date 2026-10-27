<script lang="ts">
	import RotateCw from '@lucide/svelte/icons/rotate-cw';

	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		sending: boolean;
		remaining: number;
		busy?: boolean;
		onclick: () => void;
	}

	let { sending, remaining, busy = false, onclick }: Props = $props();
</script>

<Button
	type="button"
	variant="outline"
	class="w-full"
	disabled={busy || sending || remaining > 0}
	{onclick}
>
	{#if sending}
		<Spinner data-icon="inline-start" />
		{m.common_sending()}
	{:else if remaining > 0}
		{m.verification_resend_countdown({ remaining })}
	{:else}
		<RotateCw data-icon="inline-start" />
		{m.verification_resend()}
	{/if}
</Button>
