<script lang="ts">
	import { ScanLine } from '@lucide/svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { type BarcodeFormat, readBarcode } from '#lib/utils/barcodeReader.js';

	interface Props {
		open: boolean;
		title: string;
		description: string;
		formats: readonly BarcodeFormat[];
		// Called once with the decoded text; the dialog then closes itself.
		onDetect: (text: string) => void;
	}

	let { open = $bindable(false), title, description, formats, onDetect }: Props = $props();

	type ScannerStatus = 'starting' | 'scanning' | 'denied' | 'unavailable' | 'failed';

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

	let status = $state<ScannerStatus>('starting');

	let statusMessage = $derived.by(() => {
		switch (status) {
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

	function statusForCameraError(error: unknown): ScannerStatus {
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

	// The <video> lives inside Dialog.Content, which bits-ui unmounts on close, so
	// this attachment's teardown is what releases the camera — and the camera
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
				status = 'unavailable';
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
				status = statusForCameraError(error);
				stopCamera();
				return;
			}
			status = 'scanning';
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
					status = 'failed';
					stopCamera();
					return;
				}
				if (isTornDown()) return;
				if (text !== null && text !== '') {
					onDetect(text);
					open = false;
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
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<ScanLine class="size-5 text-muted-foreground" />
				{title}
			</Dialog.Title>
			<Dialog.Description>{description}</Dialog.Description>
		</Dialog.Header>

		<div class="relative aspect-square w-full overflow-hidden rounded-xl bg-muted">
			<!-- muted + playsinline: iOS otherwise refuses to start the stream inline
			     (https://webkit.org/blog/6784/new-video-policies-for-ios/). -->
			<video
				{@attach scanFromCamera}
				class={['size-full object-cover', status !== 'scanning' && 'invisible']}
				muted
				playsinline
				aria-hidden="true"
			></video>
			<div
				class="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center text-sm text-muted-foreground"
				role="status"
			>
				{#if status === 'starting'}
					<Spinner class="size-6" />
					{m.scanner_camera_starting()}
				{:else if statusMessage}
					{statusMessage}
				{/if}
			</div>
		</div>

		<Dialog.Footer>
			<Button type="button" variant="outline" class="w-full" onclick={() => (open = false)}>
				{m.common_cancel()}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
