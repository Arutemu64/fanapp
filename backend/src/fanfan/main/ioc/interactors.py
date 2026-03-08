from dishka import Provider, Scope, provide

from fanfan.application.auth.authenticate_user import AuthenticateUser
from fanfan.application.auth.change_email import ChangeEmail
from fanfan.application.auth.change_password import ChangePassword
from fanfan.application.auth.login_telegram import LoginTelegram
from fanfan.application.auth.refresh_access_token import RefreshAccessToken
from fanfan.application.auth.register_user import RegisterUser
from fanfan.application.auth.request_email_verification import RequestEmailVerification
from fanfan.application.auth.send_email_verification import SendEmailVerification
from fanfan.application.auth.verify_email import VerifyEmail
from fanfan.application.cosplay2.sync_cosplay2 import SyncCosplay2
from fanfan.application.notifications.cancel_mailing import CancelMailing
from fanfan.application.notifications.create_role_mailing import CreateRoleMailing
from fanfan.application.notifications.delete_mailing_messages import (
    DeleteMailingMessages,
)
from fanfan.application.notifications.get_mailing_info import GetMailingInfo
from fanfan.application.notifications.list_user_notifications import (
    ListUserNotifications,
)
from fanfan.application.notifications.mark_all_read import MarkAllRead
from fanfan.application.notifications.new_notification import NewNotification
from fanfan.application.notifications.send_notification import SendNotification
from fanfan.application.notifications.send_notification_to_roles import (
    SendNotificationToRoles,
)
from fanfan.application.notifications.send_personal_notification import (
    SendMessage,
)
from fanfan.application.push_sub.create_push_subscriptions import (
    CreatePushSubscription,
)
from fanfan.application.push_sub.delete_user_push_subscription import (
    DeletePushSubscription,
)
from fanfan.application.push_sub.get_user_push_subscriptions import (
    ListUserPushSubscriptions,
)
from fanfan.application.schedule.get_schedule import (
    GetSchedule,
)
from fanfan.application.schedule_mgmt.list_schedule_changes import ListScheduleChanges
from fanfan.application.schedule_mgmt.move_event import MoveScheduleEvent
from fanfan.application.schedule_mgmt.process_schedule_change import (
    ProcessScheduleChange,
)
from fanfan.application.schedule_mgmt.set_current_event import SetCurrentScheduleEvent
from fanfan.application.schedule_mgmt.undo_change import UndoScheduleChange
from fanfan.application.schedule_mgmt.update_event_skip import UpdateScheduleEventSkip
from fanfan.application.settings.get_settings import GetSettings
from fanfan.application.settings.update_settings import UpdateSettings
from fanfan.application.sse.stream_events import StreamEvents
from fanfan.application.subscriptions.create_subscription import (
    CreateSubscription,
)
from fanfan.application.subscriptions.delete_subscription import (
    DeleteSubscription,
)
from fanfan.application.tickets.delete_ticket import DeleteTicket
from fanfan.application.tickets.link_ticket import LinkTicket
from fanfan.application.ticketscloud.process_tcloud_order import ProcessTCloudOrder
from fanfan.application.ticketscloud.sync_tcloud import SyncTCloud
from fanfan.application.users.get_current_user import GetCurrentUser
from fanfan.application.users.get_current_user_social_accounts import (
    GetCurrentUserSocialAccounts,
)
from fanfan.application.users.link_telegram_account import LinkTelegramAccount
from fanfan.application.users.unlink_telegram_account import UnlinkTelegramAccount
from fanfan.application.users.update_user import UpdateCurrentUser
from fanfan.application.users.update_user_settings import UpdateUserSettings
from fanfan.application.voting.add_vote import AddVote
from fanfan.application.voting.cancel_vote import CancelVote
from fanfan.application.voting.check_voting_contest_entry import CheckVotingContestEntry
from fanfan.application.voting.get_voting_nomination import (
    GetVotingNomination,
)
from fanfan.application.voting.get_voting_nomination_by_id import (
    GetVotingNominationById,
)
from fanfan.application.voting.get_voting_state import GetVotingState
from fanfan.application.voting.list_voting_nominations import (
    ListVotingNominations,
)


class InteractorsProvider(Provider):
    scope = Scope.REQUEST

    get_schedule_page = provide(GetSchedule)
    move_event = provide(MoveScheduleEvent)
    set_current_event = provide(SetCurrentScheduleEvent)
    toggle_event_skip = provide(UpdateScheduleEventSkip)
    revert_change = provide(UndoScheduleChange)
    proceed_schedule_change = provide(ProcessScheduleChange)
    list_schedule_changes = provide(ListScheduleChanges)

    create_mailing = provide(CreateRoleMailing)
    get_mailing_info = provide(GetMailingInfo)
    delete_mailing = provide(CancelMailing)
    proceed_mailing_cancel = provide(DeleteMailingMessages)
    send_notification = provide(SendNotification)
    send_message_to_user = provide(SendMessage)
    send_to_roles = provide(SendNotificationToRoles)

    get_nomination_by_id = provide(GetVotingNominationById)
    get_nominations_page = provide(ListVotingNominations)

    get_settings = provide(GetSettings)
    update_settings = provide(UpdateSettings)

    create_subscription = provide(CreateSubscription)
    delete_subscription = provide(DeleteSubscription)

    delete_ticket = provide(DeleteTicket)
    use_ticket = provide(LinkTicket)

    authenticate_user = provide(AuthenticateUser)
    register_user = provide(RegisterUser)
    get_current_user = provide(GetCurrentUser)
    get_current_user_social_accounts = provide(GetCurrentUserSocialAccounts)
    link_telegram_account = provide(LinkTelegramAccount)
    unlink_telegram_account = provide(UnlinkTelegramAccount)
    change_user_role = provide(UpdateCurrentUser)
    update_user_settings = provide(UpdateUserSettings)
    change_password = provide(ChangePassword)
    send_email_verification = provide(SendEmailVerification)
    request_email_verification = provide(RequestEmailVerification)
    verify_email = provide(VerifyEmail)
    change_email = provide(ChangeEmail)
    refresh_access_token = provide(RefreshAccessToken)
    login_telegram = provide(LoginTelegram)

    get_participants_page = provide(GetVotingNomination)
    add_vote = provide(AddVote)
    cancel_vote = provide(CancelVote)
    get_voting_state = provide(GetVotingState)
    check_voting_contest_entry = provide(CheckVotingContestEntry)

    sync_tcloud = provide(SyncTCloud)
    proceed_tcloud_webhook = provide(ProcessTCloudOrder)

    sync_cosplay2 = provide(SyncCosplay2)

    steam_events = provide(StreamEvents)

    create_push_subscription = provide(CreatePushSubscription)
    list_user_push_subscriptions = provide(ListUserPushSubscriptions)
    delete_push_subscription = provide(DeletePushSubscription)

    new_notification = provide(NewNotification)
    list_user_notifications = provide(ListUserNotifications)
    mark_all_read = provide(MarkAllRead)
