<script lang="ts">
	import { invalidate } from '$app/navigation';

	import type { PageProps } from './$types';

	import PushNotificationsCard from '../components/PushNotificationsCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);
</script>

<svelte:head>
	<title>Настройки уведомлений · ФАН ФАН</title>
</svelte:head>

<PushNotificationsCard {user} onSettingsUpdate={() => invalidate('app:current-user')} />
