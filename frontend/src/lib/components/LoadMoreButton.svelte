<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';

	interface Props {
		loading: boolean;
		onclick: () => void;
	}

	let { loading, onclick }: Props = $props();
</script>

<div class="mt-4 flex justify-center">
	<Button variant="outline" class="w-full sm:w-auto" {onclick} disabled={loading}>
		{#if loading}
			<Spinner data-icon="inline-start" />
		{/if}
		{loading ? 'Загрузка…' : 'Показать ещё'}
	</Button>
</div>
