// What a player's quest QR carries. The prefix lets the volunteer's scanner
// tell a player code from any other QR (a ticket, a website) before it asks
// the server about it.
const QUEST_CODE_PREFIX = 'fanfan:user:';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function questCodeFor(userId: string): string {
	return `${QUEST_CODE_PREFIX}${userId}`;
}

/** The user ID in a scanned quest code, or null when the text is not one. */
export function parseQuestCode(text: string): string | null {
	const trimmed = text.trim();
	if (!trimmed.startsWith(QUEST_CODE_PREFIX)) {
		return null;
	}
	const userId = trimmed.slice(QUEST_CODE_PREFIX.length);
	if (!UUID_PATTERN.test(userId)) {
		return null;
	}
	return userId.toLowerCase();
}
