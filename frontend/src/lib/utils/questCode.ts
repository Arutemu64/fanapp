// What a player's quest QR carries. The prefix lets the volunteer's scanner
// tell a player code from any other QR (a ticket, a website) before it asks
// the server about it. Upper case on purpose: with only A–Z, digits and ':'
// the encoder picks QR alphanumeric mode, which fits the code in version 1
// (21×21 modules), so each module is drawn larger and reads better on a dim
// screen (ISO/IEC 18004 mode table: https://www.thonky.com/qr-code-tutorial/character-capacities).
const QUEST_CODE_PREFIX = 'FANFAN:';

// Mirrors USER_NUMBER_MIN/MAX in the backend's core/vo/user.py.
const USER_NUMBER_PATTERN = /^[1-9]\d{5}$/;

export function questCodeFor(userNumber: number): string {
	return `${QUEST_CODE_PREFIX}${userNumber}`;
}

/** The user number in a scanned quest code, or null when the text is not one. */
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
