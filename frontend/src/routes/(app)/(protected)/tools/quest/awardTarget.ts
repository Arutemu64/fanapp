import type { QuestPlayerDto } from '#lib/api/generated/index.js';

export interface UnverifiedPlayer {
	number: number;
	unverified: true;
}

export type AwardTarget = QuestPlayerDto | UnverifiedPlayer;

export function isUnverified(target: AwardTarget): target is UnverifiedPlayer {
	return 'unverified' in target;
}
