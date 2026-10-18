<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { toolsFor } from '#lib/data/tools.js';
	import { m } from '#lib/paraglide/messages.js';
	import { isOrganizer } from '#lib/utils/permissions.js';

	import type { PageProps } from './$types';

	import OnlineNowCard from './components/OnlineNowCard.svelte';

	let { data }: PageProps = $props();
	// The (protected) guard's snapshot: these rows only gate links.
	let user = $derived(data.user);
	let organizer = $derived(isOrganizer(user));

	const configQuery = createQuery(() => getPublicConfigOptions());

	let tools = $derived(toolsFor(user, configQuery.data ?? FALLBACK_CONFIG));
</script>

<!-- Capped and centred like the /profile hub this menu continues. -->
<div class="mx-auto max-w-2xl">
	<SectionIntro description={m.tools_intro()} />

	<!-- Shown to every organizer, with no per-tool permission scoping the live count;
	     volunteers come here for their own tools only. -->
	{#if organizer}
		<div class="mb-4">
			<OnlineNowCard />
		</div>
	{/if}

	<!-- The /profile hub's row shape, so the toolbox reads as the next level of that
	     menu rather than a separate dashboard. -->
	<MenuGroup>
		{#each tools as tool (tool.key)}
			<MenuRow
				href={tool.href}
				label={tool.title}
				description={tool.description}
				icon={tool.icon}
			/>
		{/each}
	</MenuGroup>
</div>
