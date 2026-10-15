<script lang="ts">
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';

	// Generic content-area fallback a section shows while its first query loads,
	// when its layout can't be meaningfully skeletonised. A spinner (not a skeleton) is
	// the honest choice when the incoming shape is unknown; sections with a regular,
	// predictable layout get a bespoke skeleton instead.
</script>

<div class="flex min-h-[40vh] items-center justify-center" role="status" aria-live="polite">
	<Spinner class="size-8 text-primary" />
	<span class="sr-only">{m.common_loading()}</span>
</div>
