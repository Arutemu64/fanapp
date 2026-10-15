<script lang="ts">
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import {
		ChevronRight,
		ExternalLink,
		Globe,
		Mail,
		Map as MapIcon,
		MapPin,
		MessageCircle,
		ScrollText,
		Ticket
	} from '@lucide/svelte';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import logo from '#lib/assets/logo.svg';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import * as Item from '#lib/components/ui/item/index.js';
	import { maps } from '#lib/data/maps.js';
	import { m } from '#lib/paraglide/messages.js';

	// A text search, so there are no coordinates to keep in step with the venue.
	// https://yandex.com/dev/yandex-apps-launch-maps/doc/en/concepts/yandexmaps-web
	const yandexMapsUrl = `https://yandex.ru/maps/?text=${encodeURIComponent('Нижний Новгород, ДК ГАЗ')}`;

	interface ContactLink {
		href: string;
		label: () => string;
		/** The bare address, so people know where the row leads before leaving the app. */
		hint: string;
		icon: Component;
	}

	const facts = [
		{ label: m.guide_fact_date, value: m.guide_fact_date_value },
		{ label: m.guide_fact_place, value: m.guide_fact_place_value },
		{ label: m.guide_fact_doors, value: m.guide_fact_doors_value },
		{ label: m.guide_fact_start, value: m.guide_fact_start_value },
		{ label: m.guide_fact_kids, value: m.guide_fact_kids_value },
		{ label: m.guide_fact_age, value: m.guide_fact_age_value }
	];

	const features = [
		{ title: m.guide_feature_stage, description: m.guide_feature_stage_description },
		{ title: m.guide_feature_fair, description: m.guide_feature_fair_description },
		{ title: m.guide_feature_authors, description: m.guide_feature_authors_description },
		{ title: m.guide_feature_games, description: m.guide_feature_games_description },
		{ title: m.guide_feature_photo, description: m.guide_feature_photo_description },
		{ title: m.guide_feature_contests, description: m.guide_feature_contests_description }
	];

	const notes = [
		{ title: m.guide_note_entry, description: m.guide_note_entry_description },
		{ title: m.guide_note_belongings, description: m.guide_note_belongings_description }
	];

	const contacts: ContactLink[] = [
		{ href: 'https://fancom.info/', label: m.guide_website, hint: 'fancom.info', icon: Globe },
		{ href: 'https://vk.com/ffest_nn', label: m.guide_vk, hint: 'vk.com/ffest_nn', icon: IconVk },
		{
			href: 'https://t.me/fanfan_fest_news',
			label: m.guide_telegram,
			hint: 't.me/fanfan_fest_news',
			icon: IconTelegram
		},
		{
			href: 'https://max.ru/ffest_nn',
			label: m.guide_max,
			hint: 'max.ru/ffest_nn',
			icon: MessageCircle
		},
		{
			href: 'mailto:orgcom.fan@mail.ru',
			label: m.guide_email,
			hint: 'orgcom.fan@mail.ru',
			icon: Mail
		}
	];
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_guide() })}</title>
</svelte:head>

{#snippet externalRow(href: string, Icon: Component, title: string, description: string)}
	<Item.Root class="rounded-none">
		{#snippet child({ props })}
			<a {href} target="_blank" rel="noopener noreferrer" {...props}>
				<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
					<Icon class="size-5" aria-hidden="true" />
				</Item.Media>
				<Item.Content>
					<Item.Title class="text-base">{title}</Item.Title>
					<Item.Description>{description}</Item.Description>
				</Item.Content>
				<Item.Actions>
					<ExternalLink class="size-4 text-muted-foreground" aria-hidden="true" />
					<span class="sr-only">({m.guide_opens_in_new_tab()})</span>
				</Item.Actions>
			</a>
		{/snippet}
	</Item.Root>
{/snippet}

<!-- A hub, like /profile: an intro, then grouped rows that each lead somewhere —
     the map one level down, directions and contacts out to other apps. Grouped
     rows with a trailing indicator are the phone-settings shape for "drill in"
     (https://developer.apple.com/design/human-interface-guidelines/lists-and-tables),
     so the page reads at a glance and every target is a full-width tap. Capped
     and centred for the same reason as the profile column. -->
<div class="mx-auto flex w-full max-w-2xl flex-col gap-4 sm:gap-5">
	<section aria-labelledby="guide-heading" class="rounded-2xl border bg-card p-5 sm:p-6">
		<img src={logo} alt={m.app_name()} class="h-10 w-auto dark:invert" />
		<h2 id="guide-heading" class="mt-4 text-lg leading-snug font-semibold text-balance">
			{m.guide_tagline()}
		</h2>
		<p class="mt-2 text-muted-foreground">{m.guide_about()}</p>
	</section>

	<!-- The map is what people reach for on site, so it sits right under the intro as
	     a card with the posters themselves, not as a row among the links. -->
	<a
		href={resolve('guide/map')}
		class="group flex flex-col gap-3 rounded-2xl border bg-card p-3 shadow-sm transition-colors hover:bg-muted/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
	>
		<span class="grid grid-cols-2 gap-2">
			{#each maps as map (map.id)}
				<enhanced:img
					src={map.picture}
					alt=""
					sizes="(min-width: 672px) 320px, 45vw"
					class="block aspect-[16/10] w-full rounded-xl object-cover object-top"
				/>
			{/each}
		</span>
		<span class="flex items-center gap-3 px-2 pb-1">
			<span class="flex size-10 items-center justify-center rounded-xl bg-primary-600 text-white">
				<MapIcon class="size-5" aria-hidden="true" />
			</span>
			<span class="flex grow flex-col">
				<span class="text-lg leading-snug font-semibold">{m.nav_map()}</span>
				<span class="text-muted-foreground">{m.guide_map_description()}</span>
			</span>
			<ChevronRight class="size-5 text-muted-foreground" aria-hidden="true" />
		</span>
	</a>

	<section aria-labelledby="guide-facts" class="flex flex-col gap-2">
		<h2 id="guide-facts" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_facts_heading()}
		</h2>
		<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 rounded-2xl border bg-card p-5 sm:p-6">
			{#each facts as fact (fact.value)}
				<dt class="text-muted-foreground">{fact.label()}</dt>
				<dd class="font-medium">{fact.value()}</dd>
			{/each}
		</dl>
	</section>

	<section aria-labelledby="guide-features" class="flex flex-col gap-2">
		<h2 id="guide-features" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_features_heading()}
		</h2>
		<MenuGroup>
			{#each features as feature (feature.title)}
				<Item.Root class="rounded-none">
					<Item.Content>
						<Item.Title class="text-base">{feature.title()}</Item.Title>
						<Item.Description class="line-clamp-none">{feature.description()}</Item.Description>
					</Item.Content>
				</Item.Root>
			{/each}
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-visit" class="flex flex-col gap-2">
		<h2 id="guide-visit" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_visit_heading()}
		</h2>
		<MenuGroup>
			{@render externalRow(
				'https://fancom.info/pages/Tickets',
				Ticket,
				m.guide_buy_ticket(),
				'fancom.info/pages/Tickets'
			)}
			{@render externalRow(
				'https://fancom.info/pages/rules',
				ScrollText,
				m.guide_rules(),
				'fancom.info/pages/rules'
			)}
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-notes" class="flex flex-col gap-2">
		<h2 id="guide-notes" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_good_to_know_heading()}
		</h2>
		<MenuGroup>
			{#each notes as note (note.title)}
				<Item.Root class="rounded-none">
					<Item.Content>
						<Item.Title class="text-base">{note.title()}</Item.Title>
						<Item.Description class="line-clamp-none">{note.description()}</Item.Description>
					</Item.Content>
				</Item.Root>
			{/each}
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-directions" class="flex flex-col gap-2">
		<h2 id="guide-directions" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_directions_heading()}
		</h2>
		<MenuGroup>
			{@render externalRow(
				yandexMapsUrl,
				MapPin,
				`${m.guide_venue_name()}, ${m.guide_venue_address()}`,
				m.guide_open_in_yandex_maps()
			)}
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-contacts" class="flex flex-col gap-2">
		<h2 id="guide-contacts" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_contacts_heading()}
		</h2>
		<MenuGroup>
			{#each contacts as contact (contact.href)}
				{@render externalRow(contact.href, contact.icon, contact.label(), contact.hint)}
			{/each}
		</MenuGroup>
	</section>
</div>
