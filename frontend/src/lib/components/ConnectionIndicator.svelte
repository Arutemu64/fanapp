<script lang="ts">
	import { getEventsClient } from '$lib/events.svelte';
	import { Badge } from 'flowbite-svelte';
	import { CheckCircleSolid, ClockSolid, CloseCircleSolid } from 'flowbite-svelte-icons';

	type BadgeColor = 'green' | 'yellow' | 'red';

	let client = $derived(getEventsClient());

	let statusColor: BadgeColor = $derived(
		client?.connectionStatus === 'connected'
			? 'green'
			: client?.connectionStatus === 'transport_open'
				? 'green'
				: client?.connectionStatus === 'connecting'
					? 'yellow'
					: 'red'
	);

	let statusText = $derived(
		client?.connectionStatus === 'connected'
			? 'Онлайн'
			: client?.connectionStatus === 'transport_open'
				? 'Проверяем вход...'
				: client?.connectionStatus === 'connecting'
					? 'Подключаемся...'
					: 'Офлайн'
	);

	let StatusIcon = $derived(
		client?.connectionStatus === 'connected'
			? CheckCircleSolid
			: client?.connectionStatus === 'transport_open'
				? CheckCircleSolid
				: client?.connectionStatus === 'connecting'
					? ClockSolid
					: CloseCircleSolid
	);
</script>

<Badge color={statusColor} class="text-sm">
	<StatusIcon class="me-1.5 h-4 w-4" />
	{statusText}
</Badge>
