/**
 * Client-side twin of the backend's `apply_expected_start_times`
 * (`application/services/schedule_timing.py`, ADR-0008).
 *
 * The server computes the same projection, but against the `now` of the moment
 * it answered. Its floor — "never predict a time already in the past" — stops
 * being true the instant the response is a few seconds old, so a page left open
 * while an act overruns shows ≈ times drifting further into the past until the
 * next SSE nudge. Re-running the projection locally against a ticking clock is
 * what makes the countdown live rather than a snapshot.
 *
 * Keep the two implementations in step. The server copy is not redundant: it
 * renders the ≈ HH:MM inside subscription push notifications, where there is no
 * client to do the work.
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
 * Project each event's expected start, keyed by event id.
 *
 * `events` must be in schedule order, as `GET /schedule/` returns them. Events
 * before the current one, skipped events, and the case where nothing is on
 * stage yet are absent from the map — there is no anchor to project from.
 */
export function projectExpectedStartTimes(
	events: ProjectableEvent[],
	{ transitionBufferSeconds, nowMs }: ProjectionOptions
): Map<string, Date> {
	const projected = new Map<string, Date>();

	const currentIndex = events.findIndex((event) => event.is_current);
	if (currentIndex === -1) return projected;

	const current = events[currentIndex];
	if (!current?.actual_start_time) return projected;

	const anchorMs = new Date(current.actual_start_time).getTime();
	if (Number.isNaN(anchorMs)) return projected;

	projected.set(current.id, new Date(anchorMs));

	// Walk forward carrying a running clock. The gap added before each event is
	// the *previous* event's duration plus the buffer, so the running value
	// always names the next event's projected start.
	let runningMs = anchorMs;
	let previousDurationSeconds = current.duration_seconds;

	for (const event of events.slice(currentIndex + 1)) {
		// Skipped events consume no stage time and get no projected start.
		if (event.is_skipped) continue;

		runningMs += (previousDurationSeconds + transitionBufferSeconds) * MS_PER_SECOND;
		// Floor at now + buffer so an overrunning act pushes the tail forward
		// rather than predicting a start already past. The buffer stays in the
		// floor because even if the act ended this instant, the changeover still
		// has to happen. Carrying the clamped value forward cascades the drift.
		runningMs = Math.max(runningMs, nowMs + transitionBufferSeconds * MS_PER_SECOND);

		projected.set(event.id, new Date(runningMs));
		previousDurationSeconds = event.duration_seconds;
	}

	return projected;
}
