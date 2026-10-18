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
		/** Saves the changes; rejects with the API error body. */
		onSave: (body: UpdateCurrentUserInput) => Promise<void>;
		/** Closes the dialog when there is nothing to save. */
		onClose: () => void;
	}

	let { user, pending, onSave, onClose }: Props = $props();

	// Mounted fresh on every open (inside Dialog.Content), so each open starts from
	// the profile as it is then. `untrack` takes a one-off snapshot on purpose: a
	// background refetch of the user must not overwrite what is being typed.
	let username = $state(untrack(() => user.username));
	let avatarSeed = $state(untrack(() => user.avatar_seed));

	let usernameError = $state('');
	let formError = $state('');
	let suggestingUsername = $state(false);

	const queryClient = useQueryClient();

	// Validation patterns (must match backend)
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

	// Validate when the field is left, not on every keystroke: "Минимум 3 символа"
	// after the first letter scolds someone who is still typing
	// (https://www.nngroup.com/articles/errors-forms-design-guidelines/). Once an
	// error is showing, re-check as they type so it clears the moment it's fixed.
	function handleUsernameInput(event: Event & { currentTarget: HTMLInputElement }) {
		formError = '';
		if (usernameError) {
			usernameError = validateUsername(event.currentTarget.value);
		}
	}

	function handleUsernameBlur() {
		usernameError = validateUsername(username);
	}

	// The server generates the name: it checks the name is free, and keeps the
	// curated word lists in one place.
	async function suggestUsername() {
		suggestingUsername = true;
		formError = '';
		const usernameBeforeRequest = username;
		try {
			// A new name on every tap, so never served from the cache. `always` fails
			// at once offline instead of pausing the spinner until the network returns.
			const suggestion = await queryClient.query({
				...suggestUsernameOptions(),
				staleTime: 0,
				gcTime: 0,
				retry: false,
				networkMode: 'always'
			});
			// On slow venue wifi the field stays editable meanwhile; a name typed after
			// the tap wins over a suggestion that arrives late.
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
			// Nothing to save — close silently instead of nagging with a toast.
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

	<!-- A new face is only previewed here; it is saved with the form, so closing keeps the old one. -->
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
