<script lang="ts">
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
</script>

<div class="flex min-h-[40vh] items-center justify-center" role="status" aria-live="polite">
	<Spinner class="size-8 text-primary" />
	<span class="sr-only">{m.common_loading()}</span>
</div>
