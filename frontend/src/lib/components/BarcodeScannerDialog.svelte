<script lang="ts">
	import { ScanLine } from '@lucide/svelte';

	import type { BarcodeFormat } from '#lib/utils/barcodeReader.js';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';

	import BarcodeScanner from './BarcodeScanner.svelte';

	interface Props {
		open: boolean;
		title: string;
		description: string;
		formats: readonly BarcodeFormat[];
		// Called once with the decoded text; the dialog then closes itself.
		onDetect: (text: string) => void;
	}

	let { open = $bindable(false), title, description, formats, onDetect }: Props = $props();

	// The camera keeps reading through the close animation, and an image picked
	// just before may finish decoding after it: only the first code counts.
	function handleDetect(text: string) {
		if (!open) return;
		open = false;
		onDetect(text);
	}
</script>

<Dialog.Root bind:open>
	<!-- From sm up the dialog is centred with no height cap of its own, and the
	     camera view makes this one taller than a landscape phone. -->
	<Dialog.Content class="sm:max-h-[calc(100dvh-2rem)] sm:max-w-md sm:overflow-y-auto">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<ScanLine class="size-5 text-muted-foreground" />
				{title}
			</Dialog.Title>
			<Dialog.Description>{description}</Dialog.Description>
		</Dialog.Header>

		<!-- Inside Content, so bits-ui unmounts it on close: the camera stops and
		     every open starts from a fresh scanner state. -->
		<BarcodeScanner {formats} onDetect={handleDetect} />

		<Dialog.Footer>
			<Button type="button" variant="outline" class="w-full" onclick={() => (open = false)}>
				{m.common_cancel()}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
