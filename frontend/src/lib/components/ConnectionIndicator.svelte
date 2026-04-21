<script lang="ts">
	import { getEventsClient, type ConnectionStatus } from '$lib/services/events.svelte';
	import { Tooltip } from 'flowbite-svelte';

	type IndicatorTone = 'green' | 'yellow' | 'red';

	interface StatusDetails {
		tone: IndicatorTone;
		label: string;
		description: string;
	}

	// Keep status copy in one place so the dot color and tooltip stay in sync.
	const STATUS_DETAILS: Record<ConnectionStatus, StatusDetails> = {
		connected: {
			tone: 'green',
			label: 'Онлайн',
			description: 'Соединение активно. Новые обновления приходят сразу.'
		},
		transport_open: {
			tone: 'green',
			label: 'Проверяем вход',
			description: 'Канал связи открыт. Проверяем доступ к обновлениям.'
		},
		connecting: {
			tone: 'yellow',
			label: 'Подключаемся',
			description: 'Пытаемся заново подключиться к обновлениям.'
		},
		disconnected: {
			tone: 'red',
			label: 'Офлайн',
			description: 'Соединение остановлено. Обновления пока не приходят.'
		},
		error: {
			tone: 'red',
			label: 'Связь потеряна',
			description: 'Соединение оборвалось. Пробуем восстановить его автоматически.'
		},
		failed: {
			tone: 'red',
			label: 'Нет соединения',
			description: 'Не удалось переподключиться. Попробуй обновить страницу позже.'
		}
	};

	const TONE_CLASSES: Record<IndicatorTone, { wave: string; dot: string }> = {
		green: {
			wave: 'bg-green-500/35 dark:bg-green-400/35',
			dot: 'bg-green-500 dark:bg-green-400'
		},
		yellow: {
			wave: 'bg-yellow-400/35 dark:bg-yellow-300/35',
			dot: 'bg-yellow-400 dark:bg-yellow-300'
		},
		red: {
			wave: 'bg-red-500/35 dark:bg-red-400/35',
			dot: 'bg-red-500 dark:bg-red-400'
		}
	};

	let client = $derived(getEventsClient());
	let status = $derived(client?.connectionStatus ?? 'disconnected');
	let statusDetails = $derived(STATUS_DETAILS[status]);
	let toneClasses = $derived(TONE_CLASSES[statusDetails.tone]);
	let tooltipOpen = $state(false);
	let tooltipLabel = $derived(
		`Статус соединения: ${statusDetails.label}. Нажми или наведи, чтобы открыть подсказку.`
	);
</script>

<!-- Keep the tap target larger than the visible dot so it stays comfortable on mobile. -->
<button
	id="connection-indicator-trigger"
	type="button"
	class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white focus-visible:outline-none dark:focus-visible:ring-gray-500 dark:focus-visible:ring-offset-gray-900"
	aria-label={tooltipLabel}
	aria-expanded={tooltipOpen}
	onclick={() => (tooltipOpen = true)}
	onblur={() => (tooltipOpen = false)}
>
	<span class="relative flex h-3.5 w-3.5 items-center justify-center">
		<!-- The outer ripple adds a quick status cue without needing text in the header. -->
		<span
			class={[
				'absolute inset-0 rounded-full opacity-75 motion-safe:animate-ping',
				toneClasses.wave
			]}
		></span>
		<span
			class={[
				'relative h-3.5 w-3.5 rounded-full ring-2 ring-white dark:ring-gray-900',
				toneClasses.dot
			]}
		></span>
	</span>
</button>

<Tooltip
	trigger="hover"
	bind:isOpen={tooltipOpen}
	triggeredBy="#connection-indicator-trigger"
	placement="bottom"
	class="max-w-56 text-left text-xs leading-4 font-normal"
>
	<div class="space-y-1">
		<p class="font-semibold">{statusDetails.label}</p>
		<p>{statusDetails.description}</p>
	</div>
</Tooltip>
