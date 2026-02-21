// Voting types

export type NominationId = number;
export type VoteId = number;
export type ParticipantId = number;
export type ParticipantVotingNumber = string;

export interface VotingNominationUserDTO {
	id: NominationId;
	title: string;
	vote_id: VoteId | null;
}

export interface VotingParticipantUserDTO {
	id: ParticipantId;
	title: string;
	voting_number: ParticipantVotingNumber | null;
	vote_id: VoteId | null;
	votes_count: number;
}
