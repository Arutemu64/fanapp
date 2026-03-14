<script lang="ts">
	import { getToastService, ToastTypeColors } from '$lib/stores/toasts.svelte';
	import { Toast, ToastContainer } from 'flowbite-svelte';
	import {
		CheckCircleSolid,
		CloseCircleSolid,
		ExclamationCircleSolid
	} from 'flowbite-svelte-icons';
	import { fly } from 'svelte/transition';

	const toastService = getToastService();
</script>

<ToastContainer
	position={undefined}
	class="fixed inset-x-0 top-20 z-50 flex w-full flex-col gap-2 px-4 sm:px-6 lg:px-8"
>
	{#each toastService.items as toast (toast.id)}
		<!-- On mobile the toast uses the available width, and on larger screens it shifts to the top-right. -->
		<div class="w-full sm:ml-auto sm:max-w-sm" transition:fly={{ x: 200, duration: 300 }}>
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
