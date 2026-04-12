<script lang="ts">
	import { getToastService, ToastTypeColors } from '$lib/services/toasts.svelte';
	import { Toast, ToastContainer } from 'flowbite-svelte';
	import {
		CheckCircleSolid,
		CloseCircleSolid,
		ExclamationCircleSolid
	} from 'flowbite-svelte-icons';
	import { fly } from 'svelte/transition';

	const toastService = getToastService();
</script>

<ToastContainer>
	{#each toastService.items as toast (toast.id)}
		<!-- Keep the toast stack inside the page container so it never covers the top navbar. -->
		<div
			role={toast.type === 'error' ? 'alert' : 'status'}
			aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
			aria-atomic="true"
			class="pointer-events-auto w-full sm:ml-auto sm:max-w-sm"
			transition:fly={{ y: -16, duration: 300 }}
		>
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
