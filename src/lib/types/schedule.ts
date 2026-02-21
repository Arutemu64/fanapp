export interface ScheduleEventSubscriptionDTO {
	id: number;
	counter: number;
}

export interface ScheduleEventDTO {
	id: number;
	public_id: number;
	title: string;
	is_current: boolean;
	is_skipped: boolean;
	order: number;
	duration: number;
	queue: number | null;
	time_until: number | null;
	nomination_title: string | null;
	block_title: string | null;
	user_subscription: ScheduleEventSubscriptionDTO | null;
}

export interface GetScheduleResponse {
	schedule: ScheduleEventDTO[];
}

export type ScheduleChangeType = 'set_as_current' | 'moved' | 'skipped' | 'unskipped';

export interface ScheduleChangeEventDTO {
	id: number;
	public_id: number;
	title: string;
}

export interface ScheduleChangeUserDTO {
	id: number;
	username: string | null;
}

export interface ScheduleChangeDTO {
	id: number;
	type: ScheduleChangeType;
	mailing_id: string | null;
	user_id: number | null;
	send_global_announcement: boolean;
	changed_event: ScheduleChangeEventDTO | null;
	argument_event: ScheduleChangeEventDTO | null;
	user: ScheduleChangeUserDTO | null;
}

export interface ListScheduleChangesResponse {
	schedule_changes: ScheduleChangeDTO[];
}
