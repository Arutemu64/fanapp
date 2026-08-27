<script lang="ts">
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { ExclamationCircleOutline } from 'flowbite-svelte-icons';

	interface Props {
		/** Heading, e.g. «Голосование доступно только онлайн». Kept explicit rather
		 *  than generated: Russian agreement (доступно/доступна/доступны) varies by
		 *  the subject's gender and number. */
		title: string;
		/** One line on how to proceed, e.g. «Подключись к интернету, чтобы …». */
		message: string;
	}

	let { title, message }: Props = $props();
</script>

<!-- Shared render for surfaces that never cache and are useless offline (voting,
	feedback, tools): a mutation-only page has no saved copy to show, so it says so
	plainly. The load flags these with `offlineUnavailable` — see docs/frontend.md §2. -->
<EmptyState icon={ExclamationCircleOutline} {title} {message} />
