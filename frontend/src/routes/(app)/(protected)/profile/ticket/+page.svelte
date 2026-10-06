<script lang="ts">
	import { invalidate } from '$app/navigation';

	import type { PageProps } from './$types';

	import TicketLinkCard from '../components/TicketLinkCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);
</script>

<svelte:head>
	<title>Билет · ФАН ФАН</title>
</svelte:head>

<TicketLinkCard {user} onTicketLinked={() => invalidate('app:current-user')} />
