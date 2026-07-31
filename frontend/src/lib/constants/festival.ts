/**
 * Programme start — 22 August 2026, 11:30 Moscow time (UTC+3).
 *
 * Only a fallback signal: the organizers drive the programme by hand, so a
 * marked current act always outranks this clock (see `resolveFestivalPhase`).
 * It carries the hero countdown and decides the phase while the schedule is
 * still untouched.
 */
export const FESTIVAL_START = new Date('2026-08-22T11:30:00+03:00').getTime();
