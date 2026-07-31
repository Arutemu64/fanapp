/**
 * Client-side twin of the backend's `project_seconds_until`
 * (`application/services/schedule_timing.py`, ADR-0013).
 *
 * The API publishes anchors — when the current act actually started, how long
 * each act runs, how long a changeover takes — and each consumer works out the
 * wait itself. Doing it here against a ticking clock is what keeps «≈ 25 мин»
 * counting down while the page sits open, instead of freezing at whatever the
 * last fetch computed and going wrong the moment an act overruns.
 *
 * Keep the two implementations in step. The server copy is not redundant: it
 * renders the same wait into subscription push text, where there is no client.
 */

/** The fields the projection reads. Anything with these works, tests included. */
export interface ProjectableEvent {
	id: string;
	duration_seconds: number;
	is_current: boolean;
	is_skipped: boolean;
	// Optional as well as nullable: the field carries a default on the backend
	// DTO, so it is absent from the schema's `required` list.
	actual_start_time?: string | null;
}

export interface ProjectionOptions {
	transitionBufferSeconds: number;
	/** Current time as epoch millis, already corrected for device clock skew. */
	nowMs: number;
}

const MS_PER_SECOND = 1000;

/**
 * Seconds until each upcoming event starts, keyed by event id.
 *
 * `events` must be in schedule order, as `GET /schedule/` returns them. The
 * current event, everything before it, and skipped events are absent from the
 * map — the first two have no wait to report and the third takes no stage time.
 * An empty map means nothing is on stage, so there is no anchor to measure from.
 */
export function projectSecondsUntil(
	events: ProjectableEvent[],
	{ transitionBufferSeconds, nowMs }: ProjectionOptions
): Map<string, number> {
	const secondsUntil = new Map<string, number>();

	const currentIndex = events.findIndex((event) => event.is_current);
	if (currentIndex === -1) return secondsUntil;

	const current = events[currentIndex];
	if (!current?.actual_start_time) return secondsUntil;

	const anchorMs = new Date(current.actual_start_time).getTime();
	if (Number.isNaN(anchorMs)) return secondsUntil;

	const elapsedSeconds = (nowMs - anchorMs) / MS_PER_SECOND;
	// An act that has run past its planned length owes no more stage time, but
	// the changeover below still has to happen — which is what stops the wait
	// from going negative once a show starts slipping.
	const remainingCurrentSeconds = Math.max(0, current.duration_seconds - elapsedSeconds);

	let runningSeconds = remainingCurrentSeconds;
	for (const event of events.slice(currentIndex + 1)) {
		if (event.is_skipped) continue;

		runningSeconds += transitionBufferSeconds;
		secondsUntil.set(event.id, Math.trunc(runningSeconds));
		runningSeconds += event.duration_seconds;
	}

	return secondsUntil;
}
