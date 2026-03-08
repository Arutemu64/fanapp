<script lang="ts">
	import type { components } from '$lib/api/v1';

	interface Props {
		notification: components['schemas']['NotificationDTO'];
		compact?: boolean;
	}

	let { notification, compact = false }: Props = $props();

	// Форматируем дату один раз, чтобы шаблон оставался читаемым.
	let createdAt = $derived(new Date(notification.created_at).toLocaleString('ru'));

	function formatBody(body: string) {
		// Базово сохраняем переносы строк и убираем HTML, чтобы безопасно показать текст.
		return body
			.replace(/<br\s*\/?>/gi, '\n')
			.replace(/<\/(p|div|li|ul|ol)>/gi, '\n')
			.replace(/<[^>]+>/g, '')
			.replace(/&nbsp;/gi, ' ')
			.replace(/&amp;/gi, '&')
			.replace(/&lt;/gi, '<')
			.replace(/&gt;/gi, '>')
			.replace(/&quot;/gi, '"')
			.replace(/&#39;/gi, "'")
			.replace(/\n{3,}/g, '\n\n')
			.trim();
	}

	let bodyText = $derived(formatBody(notification.body));
</script>

<div
	class={`rounded-xl border border-gray-200 bg-white text-left shadow-sm dark:border-gray-700 dark:bg-gray-800 ${
		compact ? 'p-3' : 'p-4'
	}`}
>
	<div class="flex items-start gap-3">
		<div
			class={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${
				notification.seen_at
					? 'bg-gray-300 dark:bg-gray-600'
					: 'bg-primary-600 dark:bg-primary-500'
			}`}
		></div>

		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap items-start gap-2">
				<div
					class={`font-semibold whitespace-normal text-gray-900 dark:text-white ${
						compact ? 'text-sm' : 'text-base'
					}`}
				>
					{notification.title}
				</div>

				{#if !notification.seen_at}
					<span
						class="inline-flex rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
					>
						Новое
					</span>
				{/if}
			</div>

			<div
				class={`notification-body text-sm leading-relaxed whitespace-normal text-gray-500 dark:text-gray-400 ${
					compact ? 'mt-1' : 'mt-2'
				}`}
			>
				<div class="whitespace-pre-line">{bodyText}</div>
			</div>

			<div class="mt-2 text-xs text-primary-600 dark:text-primary-500">
				{createdAt}
			</div>
		</div>
	</div>
</div>
