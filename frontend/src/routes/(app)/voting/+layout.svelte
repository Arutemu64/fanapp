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

	// setTimeout keeps its delay in a signed 32-bit int; a longer delay overflows
	// and fires at once. Skip arming past that horizon — a convention's voting
	// window is measured in hours, and a distant boundary re-arms on the next visit.
	const MAX_TIMEOUT = 2_147_483_647;

	// The status banner is derived from the [start, end) window server-side, but the
	// window opening/closing as the wall clock crosses a boundary emits no event —
	// unlike an organizer edit (config_updated, handled in the root layout). Arm a
	// one-shot timer to the next boundary and refetch then; the fresh status and
	// window re-run this effect, which arms the following boundary. One-shot, not an
	// interval, so it costs nothing while it waits. The server stays authoritative
	// at vote time, so a missed flip is only cosmetic.
	$effect(() => {
		const bounds = [votingStatusQuery.data?.voting_start, votingStatusQuery.data?.voting_end];
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
