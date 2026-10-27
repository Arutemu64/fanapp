<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { m } from '#lib/paraglide/messages.js';
	import { currentUserOptions } from '#lib/services/identity.js';

	import type { PageProps } from './$types';

	import TicketLinkForm from '../components/TicketLinkForm.svelte';

	let { data }: PageProps = $props();
	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? data.user);
</script>

<svelte:head>
	<title>{m.document_title({ title: m.ticket_title() })}</title>
</svelte:head>

<TicketLinkForm {user} />
