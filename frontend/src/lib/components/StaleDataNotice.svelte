<script lang="ts">
	import { ClockOutline } from 'flowbite-svelte-icons';
	import NoticeCallout from './NoticeCallout.svelte';

	// Shown when a page is rendering a cached copy because the network was down.
	let {
		message = 'Нет связи. Показаны сохранённые данные — обновятся при подключении.'
	}: {
		message?: string;
	} = $props();
</script>

<NoticeCallout tone="warning" icon={ClockOutline} {message} role="status" />
