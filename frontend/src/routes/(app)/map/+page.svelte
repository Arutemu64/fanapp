<script lang="ts">
	import { asset } from '$app/paths';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import { Button } from 'flowbite-svelte';
	import { MapPinAltOutline } from 'flowbite-svelte-icons';

	interface MapEntry {
		id: string;
		title: string;
		description: string;
		src: string;
		alt: string;
	}

	// Держите этот список в sync с файлами внутри frontend/static/map.
	const maps: MapEntry[] = [
		{
			id: 'map_1',
			title: 'Карта 1',
			description: 'Откроется оригинал карты в новой вкладке.',
			src: asset('/map/map_1.jpg'),
			alt: 'Карта площадки 1'
		},
		{
			id: 'map_2_3',
			title: 'Карта 2–3',
			description: 'Откроется оригинал карты в новой вкладке.',
			src: asset('/map/map_2_3.jpg'),
			alt: 'Карта площадки 2 и 3'
		}
	];

	function openMapInNewTab(src: string) {
		window.open(src, '_blank', 'noopener,noreferrer');
	}
</script>

<svelte:head>
	<title>Карта площадки</title>
</svelte:head>

<SectionHeader
	title="Карта площадки"
	description="Нажмите на превью, чтобы открыть оригинал карты в новой вкладке и увеличить изображение привычными жестами браузера."
/>

<div class="space-y-4">
	{#each maps as map (map.id)}
		<article
			class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900"
		>
			<div class="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex items-center gap-2">
						<MapPinAltOutline class="h-5 w-5 text-primary-600 dark:text-primary-400" />
						<h2 class="text-base font-semibold text-gray-900 dark:text-white">{map.title}</h2>
					</div>
					<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						{map.description}
					</p>
				</div>

				<Button type="button" size="sm" onclick={() => openMapInNewTab(map.src)}>
					Открыть оригинал
				</Button>
			</div>

			<!-- Превью тоже работает как ссылка, чтобы пользователь мог открыть карту одним касанием. -->
			<button
				type="button"
				onclick={() => openMapInNewTab(map.src)}
				class="block w-full bg-gray-100 p-2 transition hover:bg-gray-200/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 dark:bg-gray-950 dark:hover:bg-gray-800/80"
				aria-label={`Открыть оригинал ${map.title}`}
			>
				<img
					src={map.src}
					alt={map.alt}
					loading="lazy"
					class="max-h-[70dvh] w-full rounded-xl object-contain"
				/>
			</button>
		</article>
	{:else}
		<div
			class="rounded-2xl border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400"
		>
			Карты пока не добавлены.
		</div>
	{/each}
</div>
