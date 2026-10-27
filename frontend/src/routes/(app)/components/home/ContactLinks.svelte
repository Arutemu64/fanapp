<script lang="ts">
	import type { Component } from 'svelte';

	import Globe from '@lucide/svelte/icons/globe';
	import Mail from '@lucide/svelte/icons/mail';
	import MessageCircle from '@lucide/svelte/icons/message-circle';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface ContactLink {
		href: string;
		label: () => string;
		icon: Component;
		external: boolean;
		selectable: boolean;
	}

	const EMAIL = 'orgcom.fan@mail.ru';

	const contactLinks: ContactLink[] = [
		{
			href: 'https://fancom.info/',
			label: m.guide_website,
			icon: Globe,
			external: true,
			selectable: false
		},
		{
			href: 'https://vk.com/ffest_nn',
			label: m.guide_vk,
			icon: IconVk,
			external: true,
			selectable: false
		},
		{
			href: 'https://t.me/fanfan_fest_news',
			label: m.guide_telegram,
			icon: IconTelegram,
			external: true,
			selectable: false
		},
		{
			href: 'https://max.ru/ffest_nn',
			label: m.guide_max,
			icon: MessageCircle,
			external: true,
			selectable: false
		},
		{ href: `mailto:${EMAIL}`, label: () => EMAIL, icon: Mail, external: false, selectable: true }
	];
</script>

<section aria-labelledby="guide-contacts" class="flex flex-col gap-3">
	<h2 id="guide-contacts" class="px-1 text-section text-foreground">
		{m.guide_contacts_heading()}
	</h2>
	<ul class="flex flex-wrap gap-2">
		{#each contactLinks as link (link.href)}
			<li>
				<Button
					href={link.href}
					target={link.external ? '_blank' : undefined}
					rel={link.external ? 'noopener noreferrer' : undefined}
					variant="outline"
					size="sm"
					class={link.selectable ? 'select-text' : undefined}
				>
					<link.icon data-icon="inline-start" aria-hidden="true" />
					{link.label()}
					{#if link.external}
						<span class="sr-only">({m.guide_opens_in_new_tab()})</span>
					{/if}
				</Button>
			</li>
		{/each}
	</ul>
</section>
