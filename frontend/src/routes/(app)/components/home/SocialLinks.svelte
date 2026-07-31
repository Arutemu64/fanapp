<script lang="ts">
	import { GlobeOutline } from 'flowbite-svelte-icons';
	import TelegramIcon from '~icons/simple-icons/telegram';
	import TiktokIcon from '~icons/simple-icons/tiktok';
	import VkIcon from '~icons/simple-icons/vk';

	const socials = [
		{ label: 'Официальный сайт fancom.info', href: 'https://fancom.info', icon: GlobeOutline },
		{ label: 'Telegram', href: 'https://t.me/fanfan_fest_news', icon: TelegramIcon },
		{ label: 'ВКонтакте', href: 'https://vk.com/fan_fest', icon: VkIcon },
		{ label: 'TikTok', href: 'https://www.tiktok.com/@fan_fan_official', icon: TiktokIcon }
	];
</script>

<div class="flex flex-wrap items-center gap-2">
	{#each socials as social (social.href)}
		<a
			href={social.href}
			target="_blank"
			rel="noopener noreferrer external"
			aria-label={social.label}
			class="flex h-11 w-11 items-center justify-center rounded-xl border border-gray-200 bg-gray-50 text-gray-600 transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-primary-500 dark:hover:bg-primary-900/20 dark:hover:text-primary-400"
		>
			<social.icon class="h-5 w-5" aria-hidden="true" />
		</a>
	{/each}
</div>
