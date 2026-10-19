import type { QuestPlayerDto } from '#lib/api/generated/index.js';

/**
 * A player known only by the ID in their scanned code: the lookup that would
 * name them and show their balance needs the server, and the connection is
 * down. Their award still queues (ADR-0038); the server checks the ID when it
 * is sent.
 */
export interface UnverifiedPlayer {
	id: string;
	unverified: true;
}

export type AwardTarget = QuestPlayerDto | UnverifiedPlayer;

export function isUnverified(target: AwardTarget): target is UnverifiedPlayer {
	return 'unverified' in target;
}
