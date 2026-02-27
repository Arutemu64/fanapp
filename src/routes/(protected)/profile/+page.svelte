<script lang="ts">
	import BasicUserInfoCard from '$lib/components/profile/BasicUserInfoCard.svelte';
	import TicketLinkCard from '$lib/components/profile/TicketLinkCard.svelte';
	import PushNotificationsCard from '$lib/components/profile/PushNotificationsCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import type { PageProps } from './$types';
	import { invalidateAll } from '$app/navigation';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);

	function refreshProfile() {
		invalidateAll();
	}
</script>

<svelte:head>
	<title>Профиль</title>
</svelte:head>

<SectionHeader title="Профиль" description="Управление вашим аккаунтом и информацией" />

<div class="grid items-start gap-4 sm:grid-cols-2">
	<div class="flex flex-col gap-4">
		<!-- Basic User Info Card -->
		<BasicUserInfoCard {user} onUpdate={refreshProfile} />

		<!-- Ticket Link Card -->
		<TicketLinkCard {user} onTicketLinked={refreshProfile} />
	</div>

	<div class="flex flex-col gap-4">
		<!-- Push Notifications Card -->
		<PushNotificationsCard />
	</div>
</div>
