<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';

	import { currentUserOptions } from '#lib/api/index.js';

	import type { PageProps } from './$types';

	import TicketLinkForm from '../components/TicketLinkForm.svelte';

	let { data }: PageProps = $props();
	const queryClient = useQueryClient();
	const userQuery = createQuery(() => currentUserOptions());
	// Live from the query; the guard's snapshot covers the moment a session expiry
	// has emptied it but not yet moved us to /login.
	let user = $derived(userQuery.data ?? data.user);

	function refreshUser() {
		return queryClient.invalidateQueries({ queryKey: currentUserOptions().queryKey });
	}
</script>

<svelte:head>
	<title>Билет · ФАН ФАН</title>
</svelte:head>

<TicketLinkForm {user} onTicketLinked={refreshUser} />
