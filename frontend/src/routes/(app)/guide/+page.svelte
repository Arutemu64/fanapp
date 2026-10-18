<script lang="ts">
	import type { Component } from 'svelte';

	import Globe from '@lucide/svelte/icons/globe';
	import Mail from '@lucide/svelte/icons/mail';
	import MapIcon from '@lucide/svelte/icons/map';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import MessageCircle from '@lucide/svelte/icons/message-circle';
	import ScrollText from '@lucide/svelte/icons/scroll-text';
	import { createQuery } from '@tanstack/svelte-query';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import logo from '#lib/assets/logo.svg';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { guideArticles } from '#lib/data/guideArticles.js';
	import { m } from '#lib/paraglide/messages.js';
	import { formatFestivalDate, formatFestivalTime } from '#lib/utils/formatters.js';

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

	// The date and start come from the public config organizers edit, the same source
	// as Home, so the two tabs can't disagree; the cached copy or the shipped
	// defaults fill in offline. The doors time isn't in the config.
	const configQuery = createQuery(() => getPublicConfigOptions());
	const config = $derived(configQuery.data ?? FALLBACK_CONFIG);
	const facts = $derived([
		formatFestivalDate(config.festival_start),
		m.guide_doors(),
		m.guide_start({ time: formatFestivalTime(config.festival_start) })
	]);
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_guide() })}</title>
</svelte:head>

<!-- A hub, like /profile: the intro with the facts, then grouped
     rows that each lead somewhere. Grouped rows with a trailing indicator are the
     phone-settings shape for "drill in"
     (https://developer.apple.com/design/human-interface-guidelines/lists-and-tables),
     so every target is a full-width tap. Capped and centred like the profile column.
     Read as a magazine: the tagline is the cover line, a step above the section heads,
     and each head sits over three times nearer its list than the block before it, so
     it reads as that list's title (https://practicaltypography.com/space-above-and-below.html). -->
<div class="mx-auto flex w-full max-w-2xl flex-col gap-10">
	<section aria-labelledby="guide-heading" class="rounded-2xl border bg-card p-5 sm:p-6">
		<img src={logo} alt={m.app_name()} class="h-10 w-auto dark:invert" />
		<h2 id="guide-heading" class="mt-4 text-headline text-balance">
			{m.guide_tagline()}
		</h2>
		<p class="mt-1.5 text-body leading-relaxed text-muted-foreground">{m.guide_about()}</p>
		<ul class="mt-3 flex flex-wrap gap-2">
			{#each facts as fact (fact)}
				<li class="rounded-full bg-muted px-3 py-1 text-sm font-medium">{fact}</li>
			{/each}
		</ul>
	</section>

	<section aria-labelledby="guide-important" class="flex flex-col gap-3">
		<h2 id="guide-important" class="px-1 text-section text-foreground">
			{m.guide_important_heading()}
		</h2>
		<MenuGroup>
			<MenuRow href="guide/map" label={m.nav_map()} icon={MapIcon} />
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

	<!-- Rarely needed on the day, so below the activities rather than in the hero. -->
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
