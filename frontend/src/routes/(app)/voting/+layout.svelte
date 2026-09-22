<script lang="ts">
	import {
		getVotingStatusOptions,
		getVotingStatusQueryKey
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	const eventsClient = getEventsClient();
	const queryClient = useQueryClient();
	const statusQuery = createQuery(() => getVotingStatusOptions());

	// setTimeout keeps its delay in a signed 32-bit int; a longer delay overflows
	// and fires at once. Skip arming past that horizon — a convention's voting
	// window is measured in hours, and a distant boundary re-arms on the next visit.
	const MAX_TIMEOUT = 2_147_483_647;

	// The status banner is derived from the [start, end) window server-side, but the
	// window opening/closing as the wall clock crosses a boundary emits no event —
	// unlike an organizer edit (config_updated). Arm a one-shot timer to the next
	// boundary and invalidate then; the refetch brings a fresh status and window,
	// so this effect re-runs and arms the following boundary. One-shot, not an
	// interval, so it costs nothing while it waits. The server stays authoritative
	// at vote time, so a missed flip is only cosmetic.
	const queryKey = getVotingStatusQueryKey();

	$effect(() => {
		const bounds = [statusQuery.data?.voting_start, statusQuery.data?.voting_end];
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

		const timer = setTimeout(() => void queryClient.invalidateQueries({ queryKey }), delay);
		return () => clearTimeout(timer);
	});

	onMount(() => {
		// Refetch voting status on a config change and on every (re)connect, so the
		// banner flips open/closed the moment organizers change the range — without a
		// reload — and a 'config_updated' missed while the stream was down self-heals.
		// The server still enforces the range at vote time, so a missed refresh is
		// cosmetic, never a votable dead end. Firing on first connect just re-runs the
		// freshly loaded status once — harmless and idempotent.
		const reloadStatus = () => {
			void queryClient.invalidateQueries({ queryKey });
		};

		eventsClient.on('config_updated', reloadStatus);
		eventsClient.on('connection_established', reloadStatus);

		return () => {
			eventsClient.off('config_updated', reloadStatus);
			eventsClient.off('connection_established', reloadStatus);
		};
	});
</script>

{@render children()}
