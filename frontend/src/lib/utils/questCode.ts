const QUEST_CODE_PREFIX = 'FANFAN:';

const USER_NUMBER_PATTERN = /^[1-9]\d{5}$/;

export function questCodeFor(userNumber: number): string {
	return `${QUEST_CODE_PREFIX}${userNumber}`;
}

export function parseQuestCode(text: string): number | null {
	const trimmed = text.trim().toUpperCase();
	if (!trimmed.startsWith(QUEST_CODE_PREFIX)) {
		return null;
	}
	const digits = trimmed.slice(QUEST_CODE_PREFIX.length);
	if (!USER_NUMBER_PATTERN.test(digits)) {
		return null;
	}
	return Number(digits);
}
