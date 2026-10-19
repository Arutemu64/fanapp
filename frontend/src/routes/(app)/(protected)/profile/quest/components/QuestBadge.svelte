<script lang="ts">
	import { on } from 'svelte/events';

	import type { CurrentUserDto, GetQuestOutput } from '#lib/api/generated/index.js';

	import QrCode from '#lib/components/QrCode.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import Username from '#lib/components/Username.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { questCodeFor } from '#lib/utils/questCode.js';

	interface Props {
		user: CurrentUserDto;
		/** Absent until the standings load; the code shows without them. */
		quest: GetQuestOutput | undefined;
	}

	let { user, quest }: Props = $props();

	// A player holds the code up to a volunteer and waits; a dimming screen makes
	// the scan fail. Attached to the badge, so the lock holds only while the code is
	// on screen, not while the leaderboard tab is. The browser drops the lock
	// whenever the page is hidden, so it is re-requested on return. Refusals (power
	// saving, no support) just leave the screen on its usual timeout.
	// https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API
	function keepScreenAwake() {
		if (!('wakeLock' in navigator)) {
			return;
		}
		let sentinel: WakeLockSentinel | null = null;
		let released = false;

		async function request() {
			if (document.visibilityState !== 'visible') {
				return;
			}
			try {
				const lock = await navigator.wakeLock.request('screen');
				if (released) {
					void lock.release();
					return;
				}
				sentinel = lock;
			} catch {
				// Refused: nothing to undo.
			}
		}

		void request();
		const stopListening = on(document, 'visibilitychange', () => void request());
		return () => {
			released = true;
			stopListening();
			void sentinel?.release();
		};
	}
</script>

<!-- Shaped like a festival lanyard badge: the name leads, since it is what a
     volunteer reads first and the fallback when the camera won't read the code;
     the code sits in the flat centre, and the stats close it off below a
     perforation. Badge guides put the name first and the code centred:
     https://www.zoho.com/backstage/event-badge-design-guide.html -->
<Card.Root class="mx-auto w-full max-w-sm gap-0 overflow-hidden p-0" {@attach keepScreenAwake}>
	<div class="relative flex items-end justify-between gap-3 bg-primary px-4 pt-7 pb-3">
		<!-- The lanyard slot, punched through to the page behind it. -->
		<span
			aria-hidden="true"
			class="absolute top-2.5 left-1/2 h-2 w-14 -translate-x-1/2 rounded-full bg-background"
		></span>
		<span class="font-display text-base font-bold text-primary-foreground">{m.app_name()}</span>
		<span class="text-xs font-semibold tracking-wide text-primary-foreground uppercase">
			{m.quest_title()}
		</span>
	</div>

	<div class="flex flex-col items-center gap-3 px-4 pt-5 pb-4 text-center sm:px-6">
		<div class="flex max-w-full items-center gap-3">
			<UserAvatar seed={user.avatar_seed} class="size-12" />
			<p class="min-w-0 text-start font-sans text-section text-foreground">
				<Username username={user.username} />
			</p>
		</div>
		<!-- Large and edge-to-edge on a phone: the volunteer's camera reads it from
		     arm's length, often in poor hall lighting. -->
		<QrCode
			value={questCodeFor(user.id)}
			label={m.quest_code_label({ username: user.username })}
			class="w-full max-w-64 rounded-lg"
		/>
		<p class="text-sm text-muted-foreground">{m.quest_code_hint()}</p>
	</div>

	{#if quest}
		<dl
			class="grid auto-cols-fr grid-flow-col gap-4 border-t border-dashed border-border px-4 py-3 text-center"
		>
			<div>
				<dt class="text-sm text-muted-foreground">{m.quest_summary_points()}</dt>
				<dd class="font-sans text-headline text-foreground tabular-nums">{quest.points}</dd>
			</div>
			<!-- No place until the first points: there is nothing to rank yet. -->
			{#if quest.rank !== null}
				<div>
					<dt class="text-sm text-muted-foreground">{m.quest_summary_rank()}</dt>
					<dd class="font-sans text-headline text-foreground tabular-nums">{quest.rank}</dd>
				</div>
			{/if}
		</dl>
	{/if}
</Card.Root>
