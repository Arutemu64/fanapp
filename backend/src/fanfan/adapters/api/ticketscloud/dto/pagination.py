from pydantic import BaseModel


class Pagination(BaseModel, frozen=True):
    page: int
    page_size: int
    total: int
