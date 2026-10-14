<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { currentUserOptions } from '#lib/api/index.js';
	import { m } from '#lib/paraglide/messages.js';

	import type { PageProps } from './$types';

	import TicketLinkForm from '../components/TicketLinkForm.svelte';

	let { data }: PageProps = $props();
	const userQuery = createQuery(() => currentUserOptions());
	// Live from the query; the guard's snapshot covers the moment a session expiry
	// has emptied it but not yet moved us to /login.
	let user = $derived(userQuery.data ?? data.user);
</script>

<svelte:head>
	<title>{m.profile_menu_ticket()} · {m.brand_name()}</title>
</svelte:head>

<TicketLinkForm {user} />
