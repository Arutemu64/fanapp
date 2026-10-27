<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import SearchX from '@lucide/svelte/icons/search-x';
	import { prefersReducedMotion } from 'svelte/motion';

	import EmptyState from '#lib/components/EmptyState.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SearchInput from '#lib/components/SearchInput.svelte';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import { maps, WALL_WIDTH } from '#lib/data/maps.js';
	import { m } from '#lib/paraglide/messages.js';
	import { trackEvent } from '#lib/services/analytics.js';
	import { createSearchIndex } from '#lib/utils/search.js';

	import { buildMapSelectionQuery, type MapSelection, parseMapSelection } from './mapSelection';

	let selection = $derived(parseMapSelection(page.url.searchParams));
	let floorId = $derived(selection.floorId);
	let selectedNumber = $derived(selection.placeNumber);

	let map = $derived(maps.find((entry) => entry.id === floorId));
	let selectedPoint = $derived(map?.points.find((point) => point.number === selectedNumber));

	let planElement: SVGSVGElement | undefined = $state();

	type MapEntry = (typeof maps)[number];
	type MapPoint = MapEntry['points'][number];

	interface Place {
		entry: MapEntry;
		point: MapPoint;
	}

	const searchIndex = createSearchIndex(
		maps.flatMap((entry) => entry.points.map((point) => ({ entry, point }))),
		({ point }: Place) => [point.name(), point.number]
	);
	const placeCount = maps.reduce((count, entry) => count + entry.points.length, 0);

	let searchQuery = $state('');
	let isSearching = $derived(searchQuery.trim().length > 0);
	let searchResults = $derived(searchIndex.filter(searchQuery));
	let floorPlaces = $derived.by((): Place[] => {
		const current = map;
		if (!current) return [];
		return current.points.map((point) => ({ entry: current, point }));
	});
	let listedPlaces = $derived(isSearching ? searchResults : floorPlaces);
	let resultsSummary = $derived(
		m.results_shown_of({ count: searchResults.length, total: placeCount })
	);

	function select(next: MapSelection) {
		void goto(`${resolve('map')}${buildMapSelectionQuery(next)}`, {
			replace: true,
			reset: false
		});
	}

	function getFloor() {
		return floorId;
	}

	function setFloor(id: string) {
		if (!id || id === floorId) return;
		select({ floorId: id, placeNumber: null });
	}

	function togglePoint(number: number) {
		select({ floorId, placeNumber: selectedNumber === number ? null : number });
	}

	function selectFromPlan(number: number) {
		if (selectedNumber !== number) trackEvent('map-place-select', { source: 'plan' });
		togglePoint(number);
	}

	function selectPlace(place: Place) {
		if (place.entry.id === floorId) {
			togglePoint(place.point.number);
			return;
		}
		select({ floorId: place.entry.id, placeNumber: place.point.number });
	}

	function floorLabel(place: Place): string | undefined {
		if (place.point.floor) return place.point.floor();
		if (isSearching) return place.entry.label();
		return undefined;
	}

	function selectFromList(event: MouseEvent, place: Place) {
		const deselects = place.entry.id === floorId && place.point.number === selectedNumber;
		if (!deselects) trackEvent('map-place-select', { source: 'list' });
		selectPlace(place);
		if (event.detail === 0) return;
		planElement?.scrollIntoView({
			block: 'nearest',
			behavior: prefersReducedMotion.current ? 'auto' : 'smooth'
		});
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_map() })}</title>
</svelte:head>

{#if map}
	{const plan = $derived(map.plan)}
	<div class="flex flex-col gap-4">
		<ToggleGroup.Root
			type="single"
			variant="outline"
			bind:value={getFloor, setFloor}
			aria-label={m.map_floor_switch_label()}
			class="w-full sm:w-auto"
		>
			{#each maps as entry (entry.id)}
				<ToggleGroup.Item value={entry.id} class="grow">{entry.label()}</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>

		<div class="grid items-start gap-4 lg:grid-cols-[3fr_2fr]">
			<div
				class="flex flex-col gap-3 motion-reduce:transition-none lg:sticky lg:transition-[top]"
				style:top="calc(var(--sticky-top, 0px) + 1rem)"
				style:transition-duration="var(--sticky-top-duration, 0ms)"
				style:transition-timing-function="var(--sticky-top-easing, ease-out)"
			>
				<svg
					bind:this={planElement}
					viewBox={plan.viewBox}
					role="img"
					aria-label={map.alt()}
					class="h-auto w-full rounded-2xl border bg-muted p-2 select-none"
				>
					<defs>
						<pattern
							id="stairs-{map.id}"
							width="6"
							height="6"
							patternUnits="userSpaceOnUse"
							class="stroke-muted-foreground/60"
						>
							<line x1="0" y1="3" x2="6" y2="3" stroke-width="1.5" />
						</pattern>
					</defs>

					{#each plan.stairs as stair, index (index)}
						<rect
							x={stair.x}
							y={stair.y}
							width={stair.w}
							height={stair.h}
							fill="url(#stairs-{map.id})"
						/>
					{/each}

					{#each plan.wells as well, index (index)}
						<g class="stroke-muted">
							<rect
								x={well.x}
								y={well.y}
								width={well.w}
								height={well.h}
								class="fill-foreground/55"
								stroke-width="1"
							/>
							<path
								d="M{well.x} {well.y} l{well.w} {well.h} m0 {-well.h} l{-well.w} {well.h}"
								stroke-width="1"
							/>
						</g>
					{/each}

					<path
						d={plan.walls}
						fill="none"
						stroke-width={WALL_WIDTH}
						stroke-linecap="square"
						class="stroke-foreground/55"
					/>
					{#each plan.pillars as pillar, index (index)}
						<rect
							x={pillar.x}
							y={pillar.y}
							width={pillar.w}
							height={pillar.h}
							class="fill-foreground/55"
						/>
					{/each}
					{#each plan.columns as [cx, cy, r], index (index)}
						<circle {cx} {cy} {r} class="fill-foreground/55" />
					{/each}

					{#each plan.captions as caption, index (index)}
						<text
							x={caption.x}
							y={caption.y}
							text-anchor="middle"
							dominant-baseline="central"
							font-size={plan.fontSize * 0.7}
							class="fill-muted-foreground font-semibold"
						>
							{caption.text()}
						</text>
					{/each}

					{#each plan.zones as zone, index (index)}
						{const isSelected = $derived(zone.point === selectedNumber)}
						<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
						<g
							data-point={zone.point}
							data-selected={isSelected || undefined}
							onclick={() => selectFromPlan(zone.point)}
							class={[
								'cursor-pointer transition-opacity motion-reduce:transition-none',
								selectedNumber !== null && !isSelected && 'opacity-40'
							]}
						>
							<rect
								x={zone.x}
								y={zone.y}
								width={zone.w}
								height={zone.h}
								rx="4"
								stroke-width="1.5"
								class={[isSelected ? 'fill-primary stroke-primary' : 'fill-card stroke-border']}
							/>
							<text
								x={zone.x + zone.w / 2}
								y={zone.y + zone.h / 2}
								text-anchor="middle"
								dominant-baseline="central"
								font-size={plan.fontSize}
								class={[
									'font-bold tabular-nums',
									isSelected ? 'fill-primary-foreground' : 'fill-foreground'
								]}
							>
								{zone.point}
							</text>
						</g>
					{/each}
				</svg>

				<p
					role="status"
					aria-live="polite"
					class="flex min-h-11 items-center gap-3 rounded-2xl border bg-card px-4 py-2"
				>
					{#if selectedPoint}
						<span
							class="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground tabular-nums"
						>
							{selectedPoint.number}
						</span>
						<span class="grow font-medium">{selectedPoint.name()}</span>
						{#if selectedPoint.floor}
							<span class="shrink-0 text-sm text-muted-foreground">{selectedPoint.floor()}</span>
						{/if}
					{:else}
						<span class="text-sm text-muted-foreground">{m.map_pick_hint()}</span>
					{/if}
				</p>
			</div>

			<section aria-labelledby="map-where" class="flex flex-col gap-2">
				<h2 id="map-where" class="px-1 text-section">{m.map_where_heading()}</h2>
				<SearchInput
					bind:value={searchQuery}
					name="map_search"
					label={m.map_search_label()}
					placeholder={m.map_search_placeholder()}
				/>
				<p
					role="status"
					aria-live="polite"
					class={['px-1 text-xs text-muted-foreground', !isSearching && 'sr-only']}
				>
					{#if isSearching}
						{resultsSummary}
					{/if}
				</p>
				{#if listedPlaces.length > 0}
					<MenuGroup>
						<ol class="divide-y divide-border">
							{#each listedPlaces as place (`${place.entry.id}-${place.point.number}`)}
								{const isSelected = $derived(
									place.entry.id === floorId && place.point.number === selectedNumber
								)}
								{const placeFloor = $derived(floorLabel(place))}
								<li>
									<button
										type="button"
										aria-pressed={isSelected}
										onclick={(event) => selectFromList(event, place)}
										class={[
											'flex min-h-11 w-full items-center gap-3 px-4 py-2.5 text-start transition-colors hover:bg-muted/70 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary-600',
											isSelected && 'bg-primary/10'
										]}
									>
										<span
											class={[
												'flex size-7 shrink-0 items-center justify-center rounded-md text-sm font-semibold tabular-nums',
												isSelected
													? 'bg-primary text-primary-foreground'
													: 'bg-muted text-muted-foreground'
											]}
										>
											{place.point.number}
										</span>
										<span class="grow">{place.point.name()}</span>
										{#if placeFloor}
											<span class="shrink-0 text-sm text-muted-foreground">{placeFloor}</span>
										{/if}
									</button>
								</li>
							{/each}
						</ol>
					</MenuGroup>
				{:else}
					<EmptyState
						icon={SearchX}
						title={m.common_nothing_found()}
						message={m.map_search_try_other()}
					/>
				{/if}
			</section>
		</div>
	</div>
{/if}
