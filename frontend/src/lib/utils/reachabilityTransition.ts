/**
 * Classifies a reachability-probe result into the connectivity transition the
 * offline UI should make. Pure and DOM-free so the rule can be unit-tested
 * without a browser (the OfflineService that applies it is not testable in the
 * Node runner — see docs/testing.md "Frontend").
 *
 * The rule that must not regress silently: a failed probe while the *device*
 * still reports online is treated as `confirm`, never an immediate `go-offline`.
 * On mobile, foregrounding a backgrounded tab fires the first probe before the
 * radio has finished waking, so that probe often fails transiently while the
 * connection is in fact about to succeed. Alarming on it flashes "Нет связи с
 * сервером" for a few seconds until the next probe clears it. A `false` from
 * `navigator.onLine`, by contrast, is a trustworthy negative — the device
 * really has no network — so that path commits offline at once.
 */
export type ReachabilityTransition = 'go-online' | 'go-offline' | 'confirm' | 'noop';

export function classifyReachabilityChange(opts: {
	wasOnline: boolean;
	probeReachable: boolean;
	deviceOnline: boolean;
}): ReachabilityTransition {
	if (opts.probeReachable) {
		// Recovery is always immediate; only a true offline→online edge needs the
		// caller to refresh stale pages, so a repeat "still online" is a noop.
		return opts.wasOnline ? 'noop' : 'go-online';
	}

	// Probe reports the server unreachable.
	if (!opts.wasOnline) return 'noop';
	if (!opts.deviceOnline) return 'go-offline';
	return 'confirm';
}
