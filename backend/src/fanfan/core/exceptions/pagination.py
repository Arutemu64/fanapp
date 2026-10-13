from fanfan.core.exceptions.base import ConstraintViolation


class InvalidPageCursor(ConstraintViolation):
    code = "INVALID_PAGE_CURSOR"
