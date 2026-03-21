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
	class="pointer-events-none absolute top-3 left-3 z-[70] -translate-y-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white opacity-0 shadow-lg transition-[opacity,transform] focus-visible:pointer-events-auto focus-visible:translate-y-0 focus-visible:opacity-100"
>
	{label}
</button>
