import enum
from pydantic import BaseModel

# !DEPRECATED


class AuthorizedRequest(BaseModel):
	jwt_token: str


class NewPost(AuthorizedRequest):
	title: str
	content: str


class GetPosts(AuthorizedRequest): ...


class GetPost(AuthorizedRequest):
	id_: int


class EditPost(GetPost):
	title: str = None
	content: str = None


class DeletePost(GetPost): ...


class RatePost(GetPost):
	class Rate(enum.Enum):
		LIKE = 1
		DISLIKE = 2
		REMOVE_RATE = 3

	rate: Rate
