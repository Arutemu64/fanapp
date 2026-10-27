<script lang="ts">
	import Dices from '@lucide/svelte/icons/dices';
	import User from '@lucide/svelte/icons/user';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';

	import type { CurrentUserDto, UpdateCurrentUserInput } from '#lib/api/generated/index.js';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { suggestUsernameOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { createAvatarSeed } from '#lib/utils/avatar.js';

	interface Props {
		user: CurrentUserDto;
		pending: boolean;
		onSave: (body: UpdateCurrentUserInput) => Promise<void>;
		onClose: () => void;
	}

	let { user, pending, onSave, onClose }: Props = $props();

	let username = $state(untrack(() => user.username));
	let avatarSeed = $state(untrack(() => user.avatar_seed));

	let usernameError = $state('');
	let formError = $state('');
	let suggestingUsername = $state(false);

	const queryClient = useQueryClient();

	const USERNAME_MIN_LENGTH = 3;
	const USERNAME_MAX_LENGTH = 25;
	const USERNAME_PATTERN = /^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_]{2,24}$/;

	function validateUsername(value: string): string {
		if (!value) {
			return m.username_required();
		}

		if (value.length < USERNAME_MIN_LENGTH) {
			return m.validation_min_chars({ count: USERNAME_MIN_LENGTH });
		}

		if (value.length > USERNAME_MAX_LENGTH) {
			return m.validation_max_chars({ count: USERNAME_MAX_LENGTH });
		}

		if (!USERNAME_PATTERN.test(value)) {
			return m.username_pattern();
		}

		return '';
	}

	function handleUsernameInput(event: Event & { currentTarget: HTMLInputElement }) {
		formError = '';
		if (usernameError) {
			usernameError = validateUsername(event.currentTarget.value);
		}
	}

	function handleUsernameBlur() {
		usernameError = validateUsername(username);
	}

	async function suggestUsername() {
		suggestingUsername = true;
		formError = '';
		const usernameBeforeRequest = username;
		try {
			const suggestion = await queryClient.query({
				...suggestUsernameOptions(),
				staleTime: 0,
				gcTime: 0,
				retry: false,
				networkMode: 'always'
			});
			if (username === usernameBeforeRequest) {
				username = suggestion.username;
				usernameError = '';
			}
		} catch (error) {
			formError = getApiErrorDetail(error) ?? m.username_suggestion_failed();
		} finally {
			suggestingUsername = false;
		}
	}

	function hasChanges(): boolean {
		return (!!username && username !== user.username) || avatarSeed !== user.avatar_seed;
	}

	function isValid(): boolean {
		return !usernameError;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		usernameError = validateUsername(username);

		if (!isValid()) {
			return;
		}

		if (!hasChanges()) {
			onClose();
			return;
		}

		const body: UpdateCurrentUserInput = {};
		if (username && username !== user.username) body.username = username;
		if (avatarSeed !== user.avatar_seed) body.avatar_seed = avatarSeed;

		try {
			await onSave(body);
		} catch (error) {
			const usernameFieldError = getApiFieldError(error, 'username');
			if (usernameFieldError) {
				usernameError = usernameFieldError;
				return;
			}
			formError = getApiErrorDetail(error) ?? m.profile_update_failed();
		}
	}
</script>

<form onsubmit={handleSubmit} class="flex flex-col gap-4">
	<FormError message={formError} />

	<div class="relative mx-auto">
		<UserAvatar seed={avatarSeed} class="size-32 sm:size-36" />
		<Button
			type="button"
			variant="secondary"
			size="icon"
			class="absolute right-0 bottom-0 size-11 border border-border shadow-sm"
			aria-label={m.avatar_another()}
			onclick={() => (avatarSeed = createAvatarSeed())}
		>
			<Dices aria-hidden="true" />
		</Button>
	</div>

	<Field.Field data-invalid={usernameError ? true : undefined}>
		<Field.FieldLabel for="username">{m.username_label()}</Field.FieldLabel>
		<div class="flex items-center gap-2">
			<InputGroup.Root class="flex-1">
				<InputGroup.Addon>
					<User aria-hidden="true" />
				</InputGroup.Addon>
				<InputGroup.Input
					id="username"
					name="username"
					type="text"
					placeholder={m.username_placeholder()}
					autocomplete="nickname"
					autocapitalize="off"
					spellcheck={false}
					bind:value={username}
					oninput={handleUsernameInput}
					onblur={handleUsernameBlur}
					aria-invalid={usernameError ? true : undefined}
				/>
			</InputGroup.Root>
			<Button
				type="button"
				variant="outline"
				size="icon"
				class="size-11 shrink-0"
				aria-label={m.username_another()}
				disabled={suggestingUsername}
				onclick={suggestUsername}
			>
				{#if suggestingUsername}
					<Spinner />
				{:else}
					<Dices aria-hidden="true" />
				{/if}
			</Button>
		</div>
		{#if usernameError}
			<Field.FieldError>{usernameError}</Field.FieldError>
		{/if}
		<ul class="flex flex-col gap-1 text-xs text-muted-foreground">
			<li>{m.username_rule_length({ min: USERNAME_MIN_LENGTH, max: USERNAME_MAX_LENGTH })}</li>
			<li>{m.username_rule_start()}</li>
			<li>{m.username_rule_rest()}</li>
		</ul>
	</Field.Field>

	<div class="flex flex-col-reverse gap-2 sm:grid sm:grid-cols-2">
		<Dialog.Close>
			{#snippet child({ props })}
				<Button variant="outline" {...props}>{m.common_cancel()}</Button>
			{/snippet}
		</Dialog.Close>
		<Button type="submit" disabled={pending}>
			{#if pending}
				<Spinner data-icon="inline-start" />
				{m.common_saving()}
			{:else}
				{m.common_save()}
			{/if}
		</Button>
	</div>
</form>
