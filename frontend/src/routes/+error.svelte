<script lang="ts">
	import { page } from '$app/state';
	import ErrorState from '$lib/components/ErrorState.svelte';

	let status = $derived(page.status);
	let title = $derived.by(() => {
		if (status === 403) return 'Доступ ограничен';
		if (status === 404) return 'Страница не найдена';
		return 'Что-то пошло не так';
	});
</script>

<svelte:head>
	<title>{title} ({status}) · ФАН ФАН</title>
</svelte:head>

<!-- Global fallback: no app shell above this boundary, so render full screen. -->
<ErrorState variant="fullscreen" />
