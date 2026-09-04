<script lang="ts">
	import type { FeedbackDTO } from '$lib/types/feedback';

	import * as Card from '$lib/components/ui/card';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { User } from '@lucide/svelte';

	interface Props {
		feedback: FeedbackDTO;
	}

	let { feedback }: Props = $props();

	let submittedAt = $derived(formatRelativeTime(feedback.created_at));
</script>

<Card.Root as="article" class="w-full max-w-none p-4">
	<div class="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
		<User class="size-4 shrink-0" aria-hidden="true" />
		<span class="font-semibold text-foreground">{feedback.user.username}</span>
		<span aria-hidden="true">·</span>
		<span>{submittedAt}</span>
	</div>
	<!-- Free-text feedback: Svelte escapes it, so it renders as plain text. -->
	<p class="text-sm whitespace-pre-line text-foreground">{feedback.text}</p>
</Card.Root>
