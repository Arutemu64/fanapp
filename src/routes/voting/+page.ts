import type { VotingNominationUserDTO } from '$lib/types/voting';
import { mockNominations } from '$lib/mocks/mockVoting';

export function load() {
	return {
		nominations: mockNominations as VotingNominationUserDTO[]
	};
}
