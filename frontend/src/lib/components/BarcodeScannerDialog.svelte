<script lang="ts">
	import ScanLine from '@lucide/svelte/icons/scan-line';

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
		onDetect: (text: string) => void;
	}

	let { open = $bindable(false), title, description, formats, onDetect }: Props = $props();

	function handleDetect(text: string) {
		if (!open) return;
		open = false;
		onDetect(text);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-h-[calc(100dvh-2rem)] sm:max-w-md sm:overflow-y-auto">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<ScanLine class="size-5 text-muted-foreground" />
				{title}
			</Dialog.Title>
			<Dialog.Description>{description}</Dialog.Description>
		</Dialog.Header>

		<BarcodeScanner {formats} onDetect={handleDetect} />

		<Dialog.Footer>
			<Button type="button" variant="outline" class="w-full" onclick={() => (open = false)}>
				{m.common_cancel()}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
