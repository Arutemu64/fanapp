<script lang="ts">
	import { User } from '@lucide/svelte';

	import type { FeedbackDto } from '#lib/api/generated/index.js';

	import { minuteClock } from '#lib/services/minuteClock.js';
	import { formatRelativeTime } from '#lib/utils/formatters.js';

	interface Props {
		feedback: FeedbackDto;
	}

	let { feedback }: Props = $props();

	// Ticks with the clock, so "5 минут назад" doesn't freeze on an open screen.
	let submittedAt = $derived(formatRelativeTime(feedback.created_at, minuteClock.now));
</script>

<!-- A row in FeedbackFeed's grouped list, which supplies the border and dividers. -->
<article class="p-4">
	<div class="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
		<User class="size-4 shrink-0" aria-hidden="true" />
		<span class="font-semibold text-foreground">{feedback.user.username}</span>
		<span aria-hidden="true">·</span>
		<time datetime={feedback.created_at}>{submittedAt}</time>
	</div>
	<!-- Free-text feedback: Svelte escapes it, so it renders as plain text. -->
	<p class="text-sm whitespace-pre-line text-foreground">{feedback.text}</p>
</article>
