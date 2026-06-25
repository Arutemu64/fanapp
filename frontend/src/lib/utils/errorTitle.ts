/**
 * Short Russian title for an HTTP error status. Shared by ErrorState (the
 * on-screen heading) and +error.svelte (the document <title>) so the mapping
 * lives in one place. The offline case isn't tied to a status code and is
 * handled separately in ErrorState.
 */
export function statusTitle(status: number): string {
	if (status === 403) return 'Доступ ограничен';
	if (status === 404) return 'Страница не найдена';
	return 'Что-то пошло не так';
}
