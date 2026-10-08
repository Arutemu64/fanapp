<script lang="ts">
	import { User } from '@lucide/svelte';

	import type { FeedbackDto } from '#lib/api/generated/index.js';

	import { formatRelativeTime } from '#lib/utils/formatters.js';

	interface Props {
		feedback: FeedbackDto;
	}

	let { feedback }: Props = $props();

	let submittedAt = $derived(formatRelativeTime(feedback.created_at));
</script>

<!-- A row in FeedbackFeed's grouped list, which supplies the border and dividers. -->
<article class="p-4">
	<div class="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
		<User class="size-4 shrink-0" aria-hidden="true" />
		<span class="font-semibold text-foreground">{feedback.user.username}</span>
		<span aria-hidden="true">·</span>
		<span>{submittedAt}</span>
	</div>
	<!-- Free-text feedback: Svelte escapes it, so it renders as plain text. -->
	<p class="text-sm whitespace-pre-line text-foreground">{feedback.text}</p>
</article>
