from pydantic import BaseModel
import enum


class SignUp(BaseModel):
	jwt_token: str


class LogIn(SignUp): ...


class Renew(SignUp): ...


class Status(BaseModel):
	class BasicStatus(enum.Enum):
		OK = "ok"
		ERROR = "error"  # I did this cuz i thought there might be some unknown errors

	status: BasicStatus
	details: str = None


class LogOut(Status): ...


class PostCreated(BaseModel):
	post_id: int
