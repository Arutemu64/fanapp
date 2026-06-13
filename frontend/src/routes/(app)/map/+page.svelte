<script lang="ts">
	import { asset } from '$app/paths';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { CloseOutline, DownloadOutline } from 'flowbite-svelte-icons';

	interface MapEntry {
		id: string;
		src: string;
		alt: string;
		width: number;
		height: number;
		// File name used when downloading the map.
		filename: string;
	}

	// Держите этот список в sync с файлами внутри frontend/static/map.
	const maps: MapEntry[] = [
		{
			id: 'map_1',
			src: asset('/map/map_1.jpg'),
			alt: 'Карта площадки 1',
			width: 1280,
			height: 831,
			filename: 'map_1.jpg'
		},
		{
			id: 'map_2_3',
			src: asset('/map/map_2_3.jpg'),
			alt: 'Карта площадки 2 и 3',
			width: 1280,
			height: 787,
			filename: 'map_2_3.jpg'
		}
	];

	// Currently opened map for the fullscreen viewer, or null when closed.
	let active = $state<MapEntry | null>(null);

	function close() {
		active = null;
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}
</script>

<svelte:head>
	<title>Карта площадки</title>
</svelte:head>

<SectionIntro description="Нажми на карту, чтобы открыть её на весь экран." />

<div class="space-y-4">
	{#each maps as map (map.id)}
		<button
			type="button"
			onclick={() => (active = map)}
			class="block w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-100 p-2 shadow-sm transition-colors hover:bg-gray-200/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 dark:border-gray-800 dark:bg-gray-950 dark:hover:bg-gray-800/80"
			aria-label={`Открыть карту на весь экран: ${map.alt}`}
		>
			<img
				src={map.src}
				alt={map.alt}
				width={map.width}
				height={map.height}
				loading="lazy"
				class="max-h-[70dvh] w-full rounded-xl object-contain"
			/>
		</button>
	{:else}
		<div
			class="rounded-2xl border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400"
		>
			Карты пока не добавлены.
		</div>
	{/each}
</div>

{#if active}
	<!-- Fullscreen viewer overlay. Tap the backdrop or the close button to dismiss. -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
		role="dialog"
		aria-modal="true"
		aria-label="Просмотр карты"
	>
		<!-- Full-size backdrop button sits behind the image so a tap outside it closes the viewer. -->
		<button
			type="button"
			onclick={close}
			class="absolute inset-0 cursor-default"
			aria-label="Закрыть просмотр"
		></button>

		<!-- max-w caps the size on desktop so the image isn't stretched. relative keeps it above the backdrop. -->
		<img
			src={active.src}
			alt={active.alt}
			class="relative max-h-full w-full max-w-5xl rounded-xl object-contain shadow-2xl"
		/>

		<div class="absolute end-4 top-4 z-10 flex items-center gap-2">
			<a
				href={active.src}
				download={active.filename}
				rel="external"
				class="flex h-11 w-11 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Скачать карту"
			>
				<DownloadOutline class="h-6 w-6" />
			</a>
			<button
				type="button"
				onclick={close}
				class="flex h-11 w-11 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				aria-label="Закрыть"
			>
				<CloseOutline class="h-6 w-6" />
			</button>
		</div>
	</div>
{/if}

<svelte:window onkeydown={onKeydown} />
