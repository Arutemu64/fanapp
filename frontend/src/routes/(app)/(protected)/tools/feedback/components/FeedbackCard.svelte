<script lang="ts">
	import type { FeedbackDTO } from '$lib/types/feedback';

	import { formatRelativeTime } from '$lib/utils/formatters';
	import { Card } from 'flowbite-svelte';
	import { UserCircleOutline } from 'flowbite-svelte-icons';

	interface Props {
		feedback: FeedbackDTO;
	}

	let { feedback }: Props = $props();

	let submittedAt = $derived(formatRelativeTime(feedback.created_at));
</script>

<!-- Feed card: inherits the app-wide flat, rounded-xl Card surface from the root
	+layout.svelte theme (matches the notifications and schedule-change feeds). -->
<Card class="w-full max-w-none p-4">
	<div class="mb-2 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
		<UserCircleOutline class="h-4 w-4 shrink-0" aria-hidden="true" />
		<span class="font-semibold text-gray-900 dark:text-white">{feedback.user.username}</span>
		<span aria-hidden="true">·</span>
		<span>{submittedAt}</span>
	</div>
	<!-- Free-text feedback: Svelte escapes it, so it renders as plain text. -->
	<p class="text-sm whitespace-pre-line text-gray-900 dark:text-white">{feedback.text}</p>
</Card>
