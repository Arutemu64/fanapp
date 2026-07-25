<!--
@component
Keyboard skip-to-content link, visually hidden until focused.

Wired once in `(app)/+layout.svelte` and targets `#main-content`, which must
stay focusable (`tabindex="-1"`). Both halves of that contract are load-bearing
a11y — see docs/frontend.md section 9 before moving or removing either.
-->
<script lang="ts">
	interface Props {
		targetId?: string;
		label?: string;
	}

	let { targetId = 'main-content', label = 'Перейти к содержимому' }: Props = $props();

	function skipToContent() {
		const target = document.getElementById(targetId);

		if (!(target instanceof HTMLElement)) {
			return;
		}

		target.focus();
		target.scrollIntoView({ block: 'start' });
	}
</script>

<button
	type="button"
	onclick={skipToContent}
	class="pointer-events-none absolute top-3 left-3 z-50 -translate-y-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white opacity-0 shadow-lg transition-[opacity,transform] focus:outline-none focus-visible:pointer-events-auto focus-visible:translate-y-0 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-600"
>
	{label}
</button>
