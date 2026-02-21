import type { VotingNominationUserDTO, VotingParticipantUserDTO } from '../types/voting';

// Mock nominations data
export const mockNominations: VotingNominationUserDTO[] = [
	{
		id: 1,
		title: 'Лучший вокал',
		vote_id: null
	},
	{
		id: 2,
		title: 'Лучший танец',
		vote_id: 101
	},
	{
		id: 3,
		title: 'Лучший инструментал',
		vote_id: null
	}
];

// Mock participants data by nomination
export const mockParticipantsByNomination: Record<number, VotingParticipantUserDTO[]> = {
	1: [
		// Лучший вокал
		{
			id: 1,
			title: 'Анна Смирнова',
			voting_number: 'В-01',
			vote_id: null,
			votes_count: 24
		},
		{
			id: 2,
			title: 'Дмитрий Козлов',
			voting_number: 'В-02',
			vote_id: 201,
			votes_count: 18
		},
		{
			id: 3,
			title: 'Елена Петрова',
			voting_number: 'В-03',
			vote_id: null,
			votes_count: 32
		}
	],
	2: [
		// Лучший танец
		{
			id: 4,
			title: 'Танцевальный коллектив "Ритм"',
			voting_number: 'Т-01',
			vote_id: 202,
			votes_count: 45
		},
		{
			id: 5,
			title: 'Ансамбль "Грация"',
			voting_number: 'Т-02',
			vote_id: null,
			votes_count: 38
		},
		{
			id: 6,
			title: 'Мария Сидорова',
			voting_number: 'Т-03',
			vote_id: null,
			votes_count: 52
		}
	],
	3: [
		// Лучший инструментал
		{
			id: 7,
			title: 'Иван Морозов (фортепиано)',
			voting_number: 'И-01',
			vote_id: null,
			votes_count: 19
		},
		{
			id: 8,
			title: 'Квартет "Струны"',
			voting_number: 'И-02',
			vote_id: null,
			votes_count: 28
		},
		{
			id: 9,
			title: 'Ольга Белова (скрипка)',
			voting_number: 'И-03',
			vote_id: null,
			votes_count: 41
		}
	]
};

// Helper function to get participants by nomination id
export function getParticipantsByNominationId(nominationId: number): VotingParticipantUserDTO[] {
	return mockParticipantsByNomination[nominationId] || [];
}

// Helper function to get nomination by id
export function getNominationById(id: number): VotingNominationUserDTO | undefined {
	return mockNominations.find((n) => n.id === id);
}
