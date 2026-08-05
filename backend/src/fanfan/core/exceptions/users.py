from fanfan.core.exceptions.base import (
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
)


class UserException(AppException):
    pass


class UserNotFound(NotFound, UserException):
    code = "USER_NOT_FOUND"


class UserAlreadyExists(Conflict, UserException):
    code = "USER_ALREADY_EXISTS"


class UsernameAlreadyTaken(Conflict, UserException):
    code = "USERNAME_ALREADY_TAKEN"


class UsernameProfanity(ConstraintViolation, UserException):
    code = "USERNAME_PROFANITY"


class UserHasNoEmail(Conflict, UserException):
    code = "USER_HAS_NO_EMAIL"


class EmailAlreadyExists(Conflict, UserException):
    code = "EMAIL_ALREADY_EXISTS"


class InvalidEmail(ConstraintViolation, UserException):
    code = "INVALID_EMAIL"


class SocialAccountLinkedToAnotherUser(Conflict, UserException):
    """The external account is already linked to a different local user.

    Provider-agnostic: the OAuth callback funnels every provider into the same
    `linked_to_another_account` toast, and the `(provider, subject)` unique
    constraint enforces it identically for all providers.
    """

    code = "SOCIAL_ACCOUNT_LINKED_TO_ANOTHER_USER"


class UserAlreadyHasProviderLinked(Conflict, UserException):
    """The user already has an account of this provider linked.

    Backed by the `(user_id, provider)` unique constraint — one identity per
    provider per user.
    """

    code = "USER_ALREADY_HAS_PROVIDER_LINKED"


class CannotRemoveLastSignInMethod(Conflict, UserException):
    """Unlinking would leave the user with no way to sign back in.

    A user signs in either by email — which drives both password and email-code
    login — or by a linked social account. Removing an identity is refused only
    when there is no email and it is the user's last remaining linked provider;
    otherwise the account would become unreachable. With two providers this
    replaces the old per-provider "email required to unlink" rule, which locked a
    user out of unlinking *either* account when they held both and had no email.
    """

    code = "CANNOT_REMOVE_LAST_SIGN_IN_METHOD"


class LinkInitiatorMismatch(Conflict, UserException):
    """The session that finished an account link is not the one that started it.

    Raised when the browser signed in as somebody else between the redirect to
    the provider and the callback. Attaching the identity anyway would bind
    someone else's external account to whoever happens to hold the session now,
    so the link is refused rather than retargeted.
    """

    code = "LINK_INITIATOR_MISMATCH"
