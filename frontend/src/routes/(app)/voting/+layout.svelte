<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';

	import {
		getVotingStatusOptions,
		getVotingStatusQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';

	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	const queryClient = useQueryClient();
	const votingStatusQuery = createQuery(() => getVotingStatusOptions());

	const MAX_TIMEOUT = 2_147_483_647;

	$effect(() => {
		const bounds = [
			votingStatusQuery.data?.voting_starts_at,
			votingStatusQuery.data?.voting_ends_at
		];
		const now = Date.now();
		const nextBoundary = bounds
			.filter((iso): iso is string => Boolean(iso))
			.map((iso) => new Date(iso).getTime())
			.filter((time) => time > now)
			.sort((a, b) => a - b)
			.at(0);

		if (nextBoundary === undefined) return;

		const delay = nextBoundary - now;
		if (delay > MAX_TIMEOUT) return;

		const timer = setTimeout(
			() => void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() }),
			delay
		);
		return () => clearTimeout(timer);
	});
</script>

{@render children()}
