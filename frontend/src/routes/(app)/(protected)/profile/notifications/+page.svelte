<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';

	import { currentUserOptions } from '#lib/api/index.js';

	import type { PageProps } from './$types';

	import PushNotificationsSettings from '../components/PushNotificationsSettings.svelte';

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
	<title>Настройки уведомлений · ФАН ФАН</title>
</svelte:head>

<PushNotificationsSettings {user} onSettingsUpdate={refreshUser} />
