<script lang="ts">
	import Images from '@lucide/svelte/icons/images';
	import { onDestroy } from 'svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import {
		type BarcodeFormat,
		readBarcode,
		readBarcodeFromImage
	} from '#lib/utils/barcodeReader.js';

	interface Props {
		formats: readonly BarcodeFormat[];
		onDetect: (text: string) => void;
	}

	let { formats, onDetect }: Props = $props();

	type CameraStatus = 'starting' | 'scanning' | 'denied' | 'unavailable' | 'failed';
	type ImageStatus = 'idle' | 'reading' | 'no-code' | 'unreadable';

	const CAMERA_CONSTRAINTS: MediaStreamConstraints = {
		audio: false,
		video: {
			facingMode: { ideal: 'environment' },
			width: { ideal: 1280 },
			height: { ideal: 720 }
		}
	};

	const SCAN_INTERVAL_MS = 150;

	const CORNERS = [
		'top-0 left-0 rounded-tl-lg border-t-4 border-l-4',
		'top-0 right-0 rounded-tr-lg border-t-4 border-r-4',
		'bottom-0 left-0 rounded-bl-lg border-b-4 border-l-4',
		'right-0 bottom-0 rounded-br-lg border-r-4 border-b-4'
	];

	let cameraStatus = $state<CameraStatus>('starting');
	let imageStatus = $state<ImageStatus>('idle');
	let imageInput = $state<HTMLInputElement>();

	let cameraMessage = $derived.by(() => {
		switch (cameraStatus) {
			case 'denied':
				return m.scanner_camera_denied();
			case 'unavailable':
				return m.scanner_camera_unavailable();
			case 'failed':
				return m.scanner_failed();
			default:
				return null;
		}
	});

	let imageMessage = $derived.by(() => {
		switch (imageStatus) {
			case 'no-code':
				return m.scanner_image_no_code();
			case 'unreadable':
				return m.scanner_image_unreadable();
			default:
				return null;
		}
	});

	function statusForCameraError(error: unknown): CameraStatus {
		if (!(error instanceof DOMException)) {
			return 'failed';
		}
		switch (error.name) {
			case 'NotAllowedError':
			case 'SecurityError':
				return 'denied';
			case 'NotFoundError':
			case 'OverconstrainedError':
				return 'unavailable';
			default:
				return 'failed';
		}
	}

	function captureFrame(
		video: HTMLVideoElement,
		canvas: HTMLCanvasElement,
		context: CanvasRenderingContext2D
	): ImageData {
		const { videoWidth: width, videoHeight: height } = video;
		canvas.width = width;
		canvas.height = height;
		context.drawImage(video, 0, 0, width, height);
		return context.getImageData(0, 0, width, height);
	}

	function scanFromCamera(video: HTMLVideoElement) {
		const teardown = new AbortController();
		const isTornDown = () => teardown.signal.aborted;
		let stream: MediaStream | undefined;
		let timer: ReturnType<typeof setTimeout> | undefined;
		const canvas = document.createElement('canvas');
		const context = canvas.getContext('2d', { willReadFrequently: true });

		async function start() {
			if (!('mediaDevices' in navigator) || context === null) {
				cameraStatus = 'unavailable';
				return;
			}
			try {
				stream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS);
				if (isTornDown()) {
					stopCamera();
					return;
				}
				video.srcObject = stream;
				await video.play();
			} catch (error) {
				cameraStatus = statusForCameraError(error);
				stopCamera();
				return;
			}
			cameraStatus = 'scanning';
			void readFrame();
		}

		async function readFrame() {
			if (isTornDown() || context === null) return;
			if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
				let text: string | null;
				try {
					const frame = captureFrame(video, canvas, context);
					text = await readBarcode(frame, formats);
				} catch {
					cameraStatus = 'failed';
					stopCamera();
					return;
				}
				if (isTornDown()) return;
				if (text !== null && text !== '') {
					onDetect(text);
					return;
				}
			}
			timer = setTimeout(() => void readFrame(), SCAN_INTERVAL_MS);
		}

		function stopCamera() {
			stream?.getTracks().forEach((track) => track.stop());
			stream = undefined;
			video.srcObject = null;
		}

		void start();

		return () => {
			teardown.abort();
			clearTimeout(timer);
			stopCamera();
		};
	}

	let destroyed = false;
	onDestroy(() => {
		destroyed = true;
	});

	async function handleImagePicked(event: Event & { currentTarget: HTMLInputElement }) {
		const input = event.currentTarget;
		const file = input.files?.item(0);
		input.value = '';
		if (!file) return;

		imageStatus = 'reading';
		let text: string | null;
		try {
			text = await readBarcodeFromImage(file, formats);
		} catch {
			imageStatus = 'unreadable';
			return;
		}
		if (destroyed) return;
		if (text === null || text === '') {
			imageStatus = 'no-code';
			return;
		}
		imageStatus = 'idle';
		onDetect(text);
	}
</script>

<div class="flex flex-col gap-3">
	<div class="relative aspect-4/3 w-full overflow-hidden rounded-xl bg-muted">
		<video
			{@attach scanFromCamera}
			class={['size-full object-cover', cameraStatus !== 'scanning' && 'invisible']}
			muted
			playsinline
			aria-hidden="true"
		></video>
		{#if cameraStatus === 'scanning'}
			<div class="pointer-events-none absolute inset-x-[18%] inset-y-[14%]" aria-hidden="true">
				{#each CORNERS as corner (corner)}
					<span class={['absolute size-8 border-white drop-shadow-md', corner]}></span>
				{/each}
			</div>
		{/if}
		<div
			class="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center text-sm text-muted-foreground"
			role="status"
		>
			{#if cameraStatus === 'starting'}
				<Spinner class="size-6" />
				{m.scanner_camera_starting()}
			{:else if cameraMessage}
				{cameraMessage}
			{/if}
		</div>
	</div>

	<input
		bind:this={imageInput}
		type="file"
		accept="image/jpeg,image/png,image/webp"
		hidden
		onchange={handleImagePicked}
	/>
	<Button
		type="button"
		variant="outline"
		class="w-full"
		disabled={imageStatus === 'reading'}
		onclick={() => imageInput?.click()}
	>
		{#if imageStatus === 'reading'}
			<Spinner data-icon="inline-start" />
			{m.scanner_image_reading()}
		{:else}
			<Images data-icon="inline-start" />
			{m.scanner_image_action()}
		{/if}
	</Button>
	<p class="text-center text-sm text-destructive empty:hidden" role="status">{imageMessage}</p>
</div>
