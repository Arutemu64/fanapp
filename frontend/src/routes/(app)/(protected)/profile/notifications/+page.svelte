<script lang="ts">
	import { invalidate } from '$app/navigation';

	import type { PageProps } from './$types';

	import PushNotificationsSettings from '../components/PushNotificationsSettings.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);
</script>

<svelte:head>
	<title>Настройки уведомлений · ФАН ФАН</title>
</svelte:head>

<PushNotificationsSettings {user} onSettingsUpdate={() => invalidate('app:current-user')} />
