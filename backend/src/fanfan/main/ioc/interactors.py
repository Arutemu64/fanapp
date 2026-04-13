from dishka import Provider, Scope, provide

from fanfan.application.interactors.auth.authenticate_user import AuthenticateUser
from fanfan.application.interactors.auth.authorize_telegram import AuthorizeTelegram
from fanfan.application.interactors.auth.change_email import ChangeEmail
from fanfan.application.interactors.auth.change_password import ChangePassword
from fanfan.application.interactors.auth.login_magic_link import LoginMagicLink
from fanfan.application.interactors.auth.logout_user import LogoutUser
from fanfan.application.interactors.auth.register_user import RegisterUser
from fanfan.application.interactors.auth.request_email_verification import (
    RequestEmailVerification,
)
from fanfan.application.interactors.auth.request_magic_link import RequestMagicLink
from fanfan.application.interactors.auth.send_email_verification import (
    SendEmailVerification,
)
from fanfan.application.interactors.auth.send_magic_link_email import SendMagicLinkEmail
from fanfan.application.interactors.auth.verify_email import VerifyEmail
from fanfan.application.interactors.cosplay2.sync_cosplay2 import SyncCosplay2
from fanfan.application.interactors.current_user.get_current_user import GetCurrentUser
from fanfan.application.interactors.current_user.get_current_user_social_ids import (
    GetCurrentUserSocialIds,
)
from fanfan.application.interactors.current_user.link_telegram_account import (
    LinkTelegramAccount,
)
from fanfan.application.interactors.current_user.unlink_telegram_account import (
    UnlinkTelegramAccount,
)
from fanfan.application.interactors.current_user.update_user import UpdateCurrentUser
from fanfan.application.interactors.current_user.update_user_settings import (
    UpdateUserSettings,
)
from fanfan.application.interactors.notifications.create_role_mailing import (
    CreateRoleMailing,
)
from fanfan.application.interactors.notifications.delete_mailing_messages import (
    DeleteMailingMessages,
)
from fanfan.application.interactors.notifications.get_mailing_info import GetMailingInfo
from fanfan.application.interactors.notifications.list_user_notifications import (
    ListUserNotifications,
)
from fanfan.application.interactors.notifications.mark_all_read import MarkAllRead
from fanfan.application.interactors.notifications.new_notification import (
    NewNotification,
)
from fanfan.application.interactors.notifications.send_notification import (
    SendNotification,
)
from fanfan.application.interactors.notifications.send_notification_to_roles import (
    SendNotificationToRoles,
)
from fanfan.application.interactors.notifications.send_personal_notification import (
    SendMessage,
)
from fanfan.application.interactors.notifications.send_test_notification import (
    SendTestNotification,
)
from fanfan.application.interactors.push_sub.create_push_subscriptions import (
    CreatePushSubscription,
)
from fanfan.application.interactors.push_sub.delete_user_push_subscription import (
    DeletePushSubscription,
)
from fanfan.application.interactors.push_sub.get_user_push_subscriptions import (
    ListUserPushSubscriptions,
)
from fanfan.application.interactors.schedule.get_schedule import GetSchedule
from fanfan.application.interactors.schedule_mgmt.import_schedule import ImportSchedule
from fanfan.application.interactors.schedule_mgmt.list_schedule_changes import (
    ListScheduleChanges,
)
from fanfan.application.interactors.schedule_mgmt.move_event import MoveScheduleEvent
from fanfan.application.interactors.schedule_mgmt.process_schedule_change import (
    ProcessScheduleChange,
)
from fanfan.application.interactors.schedule_mgmt.set_current_event import (
    SetCurrentScheduleEvent,
)
from fanfan.application.interactors.schedule_mgmt.undo_change import UndoScheduleChange
from fanfan.application.interactors.schedule_mgmt.update_event_skip import (
    UpdateScheduleEventSkip,
)
from fanfan.application.interactors.settings.get_settings import GetSettings
from fanfan.application.interactors.settings.update_settings import UpdateSettings
from fanfan.application.interactors.sse.stream_events import StreamEvents
from fanfan.application.interactors.subscriptions.create_subscription import (
    CreateSubscription,
)
from fanfan.application.interactors.subscriptions.delete_subscription import (
    DeleteSubscription,
)
from fanfan.application.interactors.tickets.link_ticket import LinkTicket
from fanfan.application.interactors.ticketscloud.process_tcloud_order import (
    ProcessTCloudOrder,
)
from fanfan.application.interactors.ticketscloud.sync_tcloud import SyncTCloud
from fanfan.application.interactors.voting.add_vote import AddVote
from fanfan.application.interactors.voting.cancel_vote_by_nomination import (
    CancelUserVoteByNomination,
)
from fanfan.application.interactors.voting.check_voting_contest_entry import (
    CheckVotingContestEntry,
)
from fanfan.application.interactors.voting.get_voting_nomination import (
    GetVotingNomination,
)
from fanfan.application.interactors.voting.get_voting_state import GetVotingState
from fanfan.application.interactors.voting.list_voting_nominations import (
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
    import_schedule = provide(ImportSchedule)

    create_mailing = provide(CreateRoleMailing)
    get_mailing_info = provide(GetMailingInfo)
    proceed_mailing_cancel = provide(DeleteMailingMessages)
    send_notification = provide(SendNotification)
    send_message_to_user = provide(SendMessage)
    send_to_roles = provide(SendNotificationToRoles)

    get_nominations_page = provide(ListVotingNominations)

    get_settings = provide(GetSettings)
    update_settings = provide(UpdateSettings)

    create_subscription = provide(CreateSubscription)
    delete_subscription = provide(DeleteSubscription)

    use_ticket = provide(LinkTicket)

    authenticate_user = provide(AuthenticateUser)
    register_user = provide(RegisterUser)
    get_current_user = provide(GetCurrentUser)
    get_current_user_social_accounts = provide(GetCurrentUserSocialIds)
    link_telegram_account = provide(LinkTelegramAccount)
    unlink_telegram_account = provide(UnlinkTelegramAccount)
    change_user_role = provide(UpdateCurrentUser)
    update_user_settings = provide(UpdateUserSettings)
    change_password = provide(ChangePassword)
    send_email_verification = provide(SendEmailVerification)
    send_magic_link_email = provide(SendMagicLinkEmail)
    request_email_verification = provide(RequestEmailVerification)
    request_magic_link = provide(RequestMagicLink)
    verify_email = provide(VerifyEmail)
    change_email = provide(ChangeEmail)
    login_magic_link = provide(LoginMagicLink)
    logout_user = provide(LogoutUser)
    login_telegram = provide(AuthorizeTelegram)

    get_participants_page = provide(GetVotingNomination)
    add_vote = provide(AddVote)
    cancel_vote = provide(CancelUserVoteByNomination)
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
    send_test_notification = provide(SendTestNotification)
