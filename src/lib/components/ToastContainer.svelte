<script lang="ts">
	import { toastService, ToastTypeColors } from '$lib/stores/toasts.svelte';
	import { Toast, ToastContainer } from 'flowbite-svelte';
	import {
		CheckCircleSolid,
		CloseCircleSolid,
		ExclamationCircleSolid
	} from 'flowbite-svelte-icons';
	import { fly } from 'svelte/transition';
</script>

<ToastContainer position="top-right">
	{#each toastService.items as toast (toast.id)}
		<div transition:fly={{ x: 200, duration: 300 }}>
			<Toast
				color={ToastTypeColors[toast.type]}
				dismissable={true}
				onclose={() => toastService.dismiss(toast.id)}
			>
				{#snippet icon()}
					{#if toast.type == 'success'}
						<CheckCircleSolid class="h-5 w-5" />
					{:else if toast.type == 'info'}
						<ExclamationCircleSolid class="h-5 w-5" />
					{:else if toast.type == 'warning'}
						<ExclamationCircleSolid class="h-5 w-5" />
					{:else if toast.type == 'error'}
						<CloseCircleSolid class="h-5 w-5" />
					{/if}
				{/snippet}
				{toast.message}
			</Toast>
		</div>
	{/each}
</ToastContainer>
