<script lang="ts">
	import { Images } from '@lucide/svelte';
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
		// Called with each decoded text, from the camera or a picked image.
		onDetect: (text: string) => void;
	}

	let { formats, onDetect }: Props = $props();

	type CameraStatus = 'starting' | 'scanning' | 'denied' | 'unavailable' | 'failed';
	type ImageStatus = 'idle' | 'reading' | 'no-code' | 'unreadable';

	// Rear camera where there is one, at a resolution a 1D barcode's thin bars
	// survive; `ideal` lets a laptop's single front camera still satisfy it
	// (https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).
	const CAMERA_CONSTRAINTS: MediaStreamConstraints = {
		audio: false,
		video: {
			facingMode: { ideal: 'environment' },
			width: { ideal: 1280 },
			height: { ideal: 720 }
		}
	};

	// Pause between decode attempts: a few reads a second find a code as soon as
	// it is steady, without keeping a phone's CPU busy the whole time.
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
				// NotReadableError (another app holds the camera) and the rest.
				return 'failed';
		}
	}

	// This component lives inside Dialog.Content, which bits-ui unmounts on close,
	// so this attachment's teardown is what releases the camera — and the camera
	// light — whichever way the dialog closes.
	function scanFromCamera(video: HTMLVideoElement) {
		const teardown = new AbortController();
		// A call, not a property read: TypeScript keeps a property narrowed across an
		// `await` and would call the post-decode check dead code.
		const isTornDown = () => teardown.signal.aborted;
		let stream: MediaStream | undefined;
		let timer: ReturnType<typeof setTimeout> | undefined;
		const canvas = document.createElement('canvas');
		const context = canvas.getContext('2d', { willReadFrequently: true });

		async function start() {
			// The DOM types promise `mediaDevices`, but outside a secure context or in an
			// old WebView it is missing.
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
				const { videoWidth: width, videoHeight: height } = video;
				canvas.width = width;
				canvas.height = height;
				context.drawImage(video, 0, 0, width, height);
				let text: string | null;
				try {
					text = await readBarcode(context.getImageData(0, 0, width, height), formats);
				} catch {
					// The decoder itself failed to load or run; retrying won't help.
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

	// The dialog unmounts this scanner on close. An image still decoding then (the
	// first read also waits for the decoder to load) must not deliver into a
	// dialog reopened since, which would submit a code the user cancelled.
	let destroyed = false;
	onDestroy(() => {
		destroyed = true;
	});

	// A screenshot of an e-ticket is the way to scan a code that is on this very
	// phone's screen, which the camera can't see.
	async function handleImagePicked(event: Event & { currentTarget: HTMLInputElement }) {
		const input = event.currentTarget;
		const file = input.files?.item(0);
		// Cleared so that picking the same image again still fires `change`.
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
	<!-- 4:3 rather than square keeps the sheet short enough for a small phone; the
	     decoder still reads the whole camera frame, not just the visible crop. -->
	<div class="relative aspect-4/3 w-full overflow-hidden rounded-xl bg-muted">
		<!-- muted + playsinline: iOS otherwise refuses to start the stream inline
		     (https://webkit.org/blog/6784/new-video-policies-for-ios/). -->
		<video
			{@attach scanFromCamera}
			class={['size-full object-cover', cameraStatus !== 'scanning' && 'invisible']}
			muted
			playsinline
			aria-hidden="true"
		></video>
		{#if cameraStatus === 'scanning'}
			<!-- Aiming guide only: corner brackets show where to hold the code. -->
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

	<!-- Concrete types, not `image/*`: Safari then converts a HEIC photo to JPEG
	     before we see it (https://bugs.webkit.org/show_bug.cgi?id=267277), so no
	     browser has to decode HEIC itself (Safari only can from 17, Chrome not at
	     all). A screenshot is PNG and passes through untouched. No `capture`, so a
	     phone offers its gallery rather than the camera. -->
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
	<!-- Rendered empty rather than not at all, so the live region exists before
	     its message arrives and screen readers announce it. -->
	<p class="text-center text-sm text-destructive empty:hidden" role="status">{imageMessage}</p>
</div>
