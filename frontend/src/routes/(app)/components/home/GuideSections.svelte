<script lang="ts">
	import MapPin from '@lucide/svelte/icons/map-pin';
	import ScrollText from '@lucide/svelte/icons/scroll-text';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import { guideArticles } from '#lib/data/guideArticles.js';
	import { m } from '#lib/paraglide/messages.js';

	// A text search, so there are no coordinates to keep in step with the venue.
	// https://yandex.com/dev/yandex-apps-launch-maps/doc/en/concepts/yandexmaps-web
	const yandexMapsUrl = `https://yandex.ru/maps/?text=${encodeURIComponent('Нижний Новгород, ДК ГАЗ')}`;
</script>

<!-- The festival guide under Home's live cards: grouped rows that each lead somewhere,
     the phone-settings shape for "drill in"
     (https://developer.apple.com/design/human-interface-guidelines/lists-and-tables),
     so every target is a full-width tap. Each head sits over three times nearer its list than the block before it, so it
     reads as that list's title (https://practicaltypography.com/space-above-and-below.html).
     The date and times are the hero's, so they aren't repeated here. -->
<div class="flex flex-col gap-10">
	<section aria-labelledby="guide-important" class="flex flex-col gap-3">
		<h2 id="guide-important" class="px-1 text-section text-foreground">
			{m.guide_important_heading()}
		</h2>
		<MenuGroup>
			<MenuRow
				externalHref={yandexMapsUrl}
				newTab
				label={`${m.guide_venue_name()}, ${m.guide_venue_address()}`}
				description={m.guide_open_in_yandex_maps()}
				icon={MapPin}
			/>
			<MenuRow
				externalHref="https://fancom.info/pages/rules"
				newTab
				label={m.guide_rules()}
				description={m.guide_rules_description()}
				icon={ScrollText}
			/>
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-activities" class="flex flex-col gap-3">
		<h2 id="guide-activities" class="px-1 text-section text-foreground">
			{m.guide_activities_heading()}
		</h2>
		<MenuGroup>
			{#each guideArticles as article (article.slug)}
				<MenuRow
					href={`guide/${article.slug}`}
					label={article.title}
					description={article.description}
					icon={article.icon}
				/>
			{/each}
		</MenuGroup>
	</section>
</div>
