<!--
@component
Full-width "показать ещё" button for paginated lists, with an inline spinner
while `loading`.

Owns no pagination state — the parent tracks the cursor and flips `loading`.
-->
<script lang="ts">
	import { Button, Spinner } from 'flowbite-svelte';

	interface Props {
		loading: boolean;
		onclick: () => void;
	}

	let { loading, onclick }: Props = $props();
</script>

<div class="mt-4 flex justify-center">
	<Button color="light" class="w-full sm:w-auto" {onclick} disabled={loading}>
		{#if loading}
			<Spinner size="4" class="me-2" />
		{/if}
		{loading ? 'Загрузка…' : 'Показать ещё'}
	</Button>
</div>
