from dishka import Provider, Scope, provide, provide_all

from fanfan.adapters.config.models import EnvConfig
from fanfan.application.interactors.auth.authenticate_user import AuthenticateUser
from fanfan.application.interactors.auth.authorize_social_login import (
    AuthorizeSocialLogin,
)
from fanfan.application.interactors.auth.change_email import ChangeEmail
from fanfan.application.interactors.auth.change_password import ChangePassword
from fanfan.application.interactors.auth.confirm_email_code import ConfirmEmailCode
from fanfan.application.interactors.auth.login_with_code import LoginWithCode
from fanfan.application.interactors.auth.logout_user import LogoutUser
from fanfan.application.interactors.auth.request_login_code import RequestLoginCode
from fanfan.application.interactors.auth.send_email_confirmation_code import (
    SendEmailConfirmationCode,
)
from fanfan.application.interactors.auth.send_login_code_email import SendLoginCodeEmail
from fanfan.application.interactors.cosplay.sync_cosplay import SyncCosplay
from fanfan.application.interactors.current_user.get_current_user import GetCurrentUser
from fanfan.application.interactors.current_user.link_social_account import (
    LinkSocialAccount,
)
from fanfan.application.interactors.current_user.unlink_social_account import (
    UnlinkSocialAccount,
)
from fanfan.application.interactors.current_user.update_current_user import (
    UpdateCurrentUser,
)
from fanfan.application.interactors.current_user.update_user_settings import (
    UpdateUserSettings,
)
from fanfan.application.interactors.demo.seed_demo_data import SeedDemoData
from fanfan.application.interactors.feedback.list_feedback import ListFeedback
from fanfan.application.interactors.feedback.submit_feedback import SubmitFeedback
from fanfan.application.interactors.notifications.config import NotificationConfig
from fanfan.application.interactors.notifications.create_notification import (
    CreateNotification,
)
from fanfan.application.interactors.notifications.delete_mailing_notifications import (
    DeleteMailingNotifications,
)
from fanfan.application.interactors.notifications.get_notification import (
    GetNotification,
)
from fanfan.application.interactors.notifications.get_unread_count import (
    GetUnreadNotificationsCount,
)
from fanfan.application.interactors.notifications.list_user_notifications import (
    ListUserNotifications,
)
from fanfan.application.interactors.notifications.mark_all_read import MarkAllRead
from fanfan.application.interactors.notifications.mark_read import (
    MarkNotificationsRead,
)
from fanfan.application.interactors.notifications.process_broadcast import (
    ProcessBroadcast,
)
from fanfan.application.interactors.notifications.purge_notifications import (
    PurgeNotifications,
)
from fanfan.application.interactors.notifications.send_broadcast import (
    SendBroadcast,
)
from fanfan.application.interactors.notifications.send_notification import (
    SendNotification,
)
from fanfan.application.interactors.notifications.send_personal_notification import (
    SendPersonalNotification,
)
from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
)
from fanfan.application.interactors.notifications.send_test_notification import (
    SendTestNotification,
)
from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.application.interactors.outbox.publish_outbox_events import (
    PublishOutboxEvents,
)
from fanfan.application.interactors.outbox.purge_outbox_events import (
    PurgeOutboxEvents,
)
from fanfan.application.interactors.permissions.grant_permission import (
    GrantPermission,
)
from fanfan.application.interactors.permissions.list_user_permissions import (
    ListUserPermissions,
)
from fanfan.application.interactors.permissions.revoke_permission import (
    RevokePermission,
)
from fanfan.application.interactors.push_sub.check_push_subscription import (
    CheckPushSubscription,
)
from fanfan.application.interactors.push_sub.create_push_subscription import (
    CreatePushSubscription,
)
from fanfan.application.interactors.push_sub.delete_push_subscription import (
    DeletePushSubscription,
)
from fanfan.application.interactors.schedule.get_schedule import GetSchedule
from fanfan.application.interactors.schedule_mgmt.import_schedule import ImportSchedule
from fanfan.application.interactors.schedule_mgmt.list_schedule_changes import (
    ListScheduleChanges,
)
from fanfan.application.interactors.schedule_mgmt.move_schedule_event import (
    MoveScheduleEvent,
)
from fanfan.application.interactors.schedule_mgmt.set_current_schedule_event import (
    SetCurrentScheduleEvent,
)
from fanfan.application.interactors.schedule_mgmt.undo_schedule_change import (
    UndoScheduleChange,
)
from fanfan.application.interactors.schedule_mgmt.update_schedule_event_skip import (
    UpdateScheduleEventSkip,
)
from fanfan.application.interactors.settings.get_public_config import GetPublicConfig
from fanfan.application.interactors.settings.get_settings import GetSettings
from fanfan.application.interactors.settings.update_settings import UpdateSettings
from fanfan.application.interactors.sse.stream_events import StreamEvents
from fanfan.application.interactors.subscriptions.create_subscription import (
    CreateSubscription,
)
from fanfan.application.interactors.subscriptions.delete_subscription import (
    DeleteSubscription,
)
from fanfan.application.interactors.subscriptions.get_subscriptions import (
    GetSubscriptions,
)
from fanfan.application.interactors.tickets.generate_tickets import GenerateTickets
from fanfan.application.interactors.tickets.link_ticket import LinkTicket
from fanfan.application.interactors.tickets.process_ticket_order import (
    ProcessTicketOrder,
)
from fanfan.application.interactors.tickets.sync_tickets import SyncTickets
from fanfan.application.interactors.users.create_user import CreateUser
from fanfan.application.interactors.users.get_user import GetUser
from fanfan.application.interactors.users.list_users import ListUsers
from fanfan.application.interactors.voting.add_vote import AddVote
from fanfan.application.interactors.voting.cancel_vote import (
    CancelVote,
)
from fanfan.application.interactors.voting.draw_voting_contest_winner import (
    DrawVotingContestWinner,
)
from fanfan.application.interactors.voting.get_voting_dashboard import (
    GetVotingDashboard,
)
from fanfan.application.interactors.voting.get_voting_nomination import (
    GetVotingNomination,
)
from fanfan.application.interactors.voting.get_voting_state import GetVotingState
from fanfan.application.interactors.voting.list_voting_nominations import (
    ListVotingNominations,
)
from fanfan.application.interactors.voting.set_voting_time_range import (
    SetVotingTimeRange,
)


class InteractorsProvider(Provider):
    scope = Scope.REQUEST

    # Tuning slices consumed only by the interactors below (outbox relay/purge,
    # notification purge), unpacked here so they live with their consumers.
    @provide(scope=Scope.APP)
    def get_outbox_config(self, config: EnvConfig) -> OutboxConfig:
        return config.outbox

    @provide(scope=Scope.APP)
    def get_notification_config(self, config: EnvConfig) -> NotificationConfig:
        return config.notification

    # Every interactor is request-scoped and provides itself, so one
    # provide_all keeps the roster flat instead of one binding line each.
    interactors = provide_all(
        GetSchedule,
        MoveScheduleEvent,
        SetCurrentScheduleEvent,
        UpdateScheduleEventSkip,
        UndoScheduleChange,
        SendScheduleChangeNotifications,
        ListScheduleChanges,
        ImportSchedule,
        SeedDemoData,
        GrantPermission,
        RevokePermission,
        ListUserPermissions,
        SendBroadcast,
        GetNotification,
        DeleteMailingNotifications,
        SendNotification,
        SendPersonalNotification,
        ProcessBroadcast,
        ListVotingNominations,
        GetPublicConfig,
        GetSettings,
        UpdateSettings,
        CreateSubscription,
        DeleteSubscription,
        GetSubscriptions,
        LinkTicket,
        SubmitFeedback,
        ListFeedback,
        ListUsers,
        GetUser,
        CreateUser,
        AuthenticateUser,
        GetCurrentUser,
        LinkSocialAccount,
        UnlinkSocialAccount,
        UpdateCurrentUser,
        UpdateUserSettings,
        ChangePassword,
        SendEmailConfirmationCode,
        SendLoginCodeEmail,
        RequestLoginCode,
        ConfirmEmailCode,
        ChangeEmail,
        LoginWithCode,
        LogoutUser,
        AuthorizeSocialLogin,
        GetVotingNomination,
        AddVote,
        CancelVote,
        GetVotingState,
        GetVotingDashboard,
        SetVotingTimeRange,
        DrawVotingContestWinner,
        SyncTickets,
        ProcessTicketOrder,
        GenerateTickets,
        SyncCosplay,
        StreamEvents,
        CreatePushSubscription,
        CheckPushSubscription,
        DeletePushSubscription,
        PublishOutboxEvents,
        PurgeOutboxEvents,
        PurgeNotifications,
        CreateNotification,
        ListUserNotifications,
        MarkAllRead,
        MarkNotificationsRead,
        GetUnreadNotificationsCount,
        SendTestNotification,
    )
