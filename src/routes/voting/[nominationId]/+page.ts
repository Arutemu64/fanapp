import type { VotingParticipantUserDTO, VotingNominationUserDTO } from '$lib/types/voting';
import { getParticipantsByNominationId, getNominationById } from '$lib/mocks/mockVoting';
import { error } from '@sveltejs/kit';

export function load({ params }) {
	const nominationId = parseInt(params.nominationId);
	const nomination = getNominationById(nominationId);

	if (!nomination) {
		throw error(404, 'Номинация не найдена');
	}

	const participants = getParticipantsByNominationId(nominationId);

	return {
		nomination: nomination as VotingNominationUserDTO,
		participants: participants as VotingParticipantUserDTO[]
	};
}
