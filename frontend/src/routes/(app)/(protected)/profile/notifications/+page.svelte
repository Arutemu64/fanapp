<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { m } from '#lib/paraglide/messages.js';
	import { currentUserOptions } from '#lib/services/identity.js';

	import type { PageProps } from './$types';

	import PushNotificationsSettings from '../components/PushNotificationsSettings.svelte';

	let { data }: PageProps = $props();
	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? data.user);
</script>

<svelte:head>
	<title>{m.document_title({ title: m.notifications_settings_title() })}</title>
</svelte:head>

<PushNotificationsSettings {user} />
