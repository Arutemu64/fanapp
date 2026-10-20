<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import { maps, WALL_WIDTH } from '#lib/data/maps.js';
	import { m } from '#lib/paraglide/messages.js';

	let floorId = $state(maps[0]?.id ?? '');
	let selectedNumber = $state<number | null>(null);

	let map = $derived(maps.find((entry) => entry.id === floorId));
	let selectedPoint = $derived(map?.points.find((point) => point.number === selectedNumber));

	let planElement: SVGSVGElement | undefined = $state();

	function getFloor() {
		return floorId;
	}

	// A single-select ToggleGroup hands back '' when the pressed item is tapped
	// again; a floor must always be shown, so that tap changes nothing.
	function setFloor(id: string) {
		if (!id) return;
		floorId = id;
		selectedNumber = null;
	}

	function togglePoint(number: number) {
		selectedNumber = selectedNumber === number ? null : number;
	}

	// On a phone the list runs below the plan, so a row tapped far down would
	// light up a zone off screen. `nearest` scrolls only when the plan isn't
	// already in view; the layout's scroll-padding keeps it clear of the navbar.
	// Only for a tap or click: Enter/Space fire a click with `detail` 0, and
	// scrolling then would carry the focused row off screen (WCAG 2.4.11); the
	// status line still announces the pick.
	function selectFromList(event: MouseEvent, number: number) {
		togglePoint(number);
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

		<!-- Two columns once there's room, so the plan stays in view beside its
		list; on a phone the list follows the plan. -->
		<div class="grid items-start gap-4 lg:grid-cols-[3fr_2fr]">
			<!-- Sticks below the top chrome through the (app) layout's --sticky-top,
			which follows the bar as it hides and the connection banner as it shows. -->
			<div
				class="flex flex-col gap-3 motion-reduce:transition-none lg:sticky lg:transition-[top]"
				style:top="calc(var(--sticky-top, 0px) + 1rem)"
				style:transition-duration="var(--sticky-top-duration, 0ms)"
				style:transition-timing-function="var(--sticky-top-easing, ease-out)"
			>
				<!-- The plan is a picture to sighted users and one image to a screen
				reader: the list below carries every place by name and is the keyboard
				path to the same selection, so the zones stay pointer-only rather than
				doubling every tab stop. -->
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
						<!-- Pointer-only by design; the list below is the keyboard path (see above). -->
						<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
						<g
							data-point={zone.point}
							data-selected={isSelected || undefined}
							onclick={() => togglePoint(zone.point)}
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
				<MenuGroup>
					<ol class="divide-y divide-border">
						{#each map.points as point (point.number)}
							{const isSelected = $derived(point.number === selectedNumber)}
							<li>
								<button
									type="button"
									aria-pressed={isSelected}
									onclick={(event) => selectFromList(event, point.number)}
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
										{point.number}
									</span>
									<span class="grow">{point.name()}</span>
									{#if point.floor}
										<span class="shrink-0 text-sm text-muted-foreground">{point.floor()}</span>
									{/if}
								</button>
							</li>
						{/each}
					</ol>
				</MenuGroup>
			</section>
		</div>
	</div>
{/if}
