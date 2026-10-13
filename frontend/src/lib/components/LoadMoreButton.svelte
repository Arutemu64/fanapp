<script lang="ts">
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';

	interface Props {
		// The next page is loading: shows the spinner.
		loading: boolean;
		// Any fetch of the list is running. A background refetch rewrites every
		// loaded page, and fetching the next one meanwhile can overwrite it
		// (https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries).
		busy: boolean;
		onclick: () => void;
	}

	let { loading, busy, onclick }: Props = $props();
</script>

<div class="mt-4 flex justify-center">
	<Button variant="outline" class="w-full sm:w-auto" {onclick} disabled={busy}>
		{#if loading}
			<Spinner data-icon="inline-start" />
		{/if}
		{loading ? 'Загрузка…' : 'Показать ещё'}
	</Button>
</div>
