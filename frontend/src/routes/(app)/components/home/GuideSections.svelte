<script lang="ts">
	import type { Component } from 'svelte';

	import Globe from '@lucide/svelte/icons/globe';
	import Mail from '@lucide/svelte/icons/mail';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import MessageCircle from '@lucide/svelte/icons/message-circle';
	import ScrollText from '@lucide/svelte/icons/scroll-text';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import { guideArticles } from '#lib/data/guideArticles.js';
	import { m } from '#lib/paraglide/messages.js';
	import { formatFestivalDate, formatFestivalTime } from '#lib/utils/formatters.js';

	interface Props {
		/** The configured start, the same one the hero counts down to. */
		festivalStart: string;
	}

	let { festivalStart }: Props = $props();

	// Before the festival the hero shows only a countdown, so the date and start
	// are spelled out here for anyone planning the trip. The doors time isn't in
	// the config.
	let facts = $derived([
		formatFestivalDate(festivalStart),
		m.guide_doors(),
		m.guide_start({ time: formatFestivalTime(festivalStart) })
	]);

	// A text search, so there are no coordinates to keep in step with the venue.
	// https://yandex.com/dev/yandex-apps-launch-maps/doc/en/concepts/yandexmaps-web
	const yandexMapsUrl = `https://yandex.ru/maps/?text=${encodeURIComponent('Нижний Новгород, ДК ГАЗ')}`;

	interface ContactLink {
		href: string;
		label: () => string;
		/** The handle or address, so a row is recognisable without its icon. */
		handle: string;
		icon: Component;
		/** mailto: stays in the app's tab; web links open elsewhere. */
		external: boolean;
	}

	const contactLinks: ContactLink[] = [
		{
			href: 'https://fancom.info/',
			label: m.guide_website,
			handle: 'fancom.info',
			icon: Globe,
			external: true
		},
		{
			href: 'https://vk.com/ffest_nn',
			label: m.guide_vk,
			handle: 'vk.com/ffest_nn',
			icon: IconVk,
			external: true
		},
		{
			href: 'https://t.me/fanfan_fest_news',
			label: m.guide_telegram,
			handle: 't.me/fanfan_fest_news',
			icon: IconTelegram,
			external: true
		},
		{
			href: 'https://max.ru/ffest_nn',
			label: m.guide_max,
			handle: 'max.ru/ffest_nn',
			icon: MessageCircle,
			external: true
		},
		{
			href: 'mailto:orgcom.fan@mail.ru',
			label: m.guide_email,
			handle: 'orgcom.fan@mail.ru',
			icon: Mail,
			external: false
		}
	];
</script>

<!-- The festival guide under Home's live cards: grouped rows that each lead somewhere,
     the phone-settings shape for "drill in"
     (https://developer.apple.com/design/human-interface-guidelines/lists-and-tables),
     so every target is a full-width tap. Each head sits over three times nearer its list than the block before it, so it
     reads as that list's title (https://practicaltypography.com/space-above-and-below.html). -->
<div class="flex flex-col gap-10">
	<section aria-labelledby="guide-important" class="flex flex-col gap-3">
		<h2 id="guide-important" class="px-1 text-section text-foreground">
			{m.guide_important_heading()}
		</h2>
		<ul class="flex flex-wrap gap-2 px-1">
			{#each facts as fact (fact)}
				<li class="rounded-full bg-muted px-3 py-1 text-sm font-medium">{fact}</li>
			{/each}
		</ul>
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

	<!-- Rarely needed on the day, so last. -->
	<section aria-labelledby="guide-contacts" class="flex flex-col gap-3">
		<h2 id="guide-contacts" class="px-1 text-section text-foreground">
			{m.guide_contacts_heading()}
		</h2>
		<MenuGroup>
			{#each contactLinks as link (link.href)}
				<MenuRow
					externalHref={link.href}
					newTab={link.external}
					label={link.label()}
					description={link.handle}
					icon={link.icon}
				/>
			{/each}
		</MenuGroup>
	</section>
</div>
