<script lang="ts">
	import { invalidate } from '$app/navigation';

	import type { PageProps } from './$types';

	import TicketLinkForm from '../components/TicketLinkForm.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);
</script>

<svelte:head>
	<title>Билет · ФАН ФАН</title>
</svelte:head>

<TicketLinkForm {user} onTicketLinked={() => invalidate('app:current-user')} />
