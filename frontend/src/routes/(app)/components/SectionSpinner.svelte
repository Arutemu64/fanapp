<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner';

	// Generic content-area fallback shown by the app shell while a section whose
	// layout we can't meaningfully skeletonise loads. A spinner (not a skeleton) is
	// the honest choice when the incoming shape is unknown; sections with a regular,
	// predictable layout get a bespoke skeleton instead.
</script>

<div class="flex min-h-[40vh] items-center justify-center" role="status" aria-live="polite">
	<Spinner class="size-8 text-primary" />
	<span class="sr-only">Загрузка…</span>
</div>
