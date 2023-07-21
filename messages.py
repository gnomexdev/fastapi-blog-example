import config

INVALID_NICK = f"Invalid nickname symbols. Only [a-z A-Z 0-9 _] symbols are allowed." \
               f"You cannot put 2 underscores together or an underscore in the end/start of the nickname. " \
               f"Min length: {config.MIN_NICKNAME_LENGTH}. Max length: {config.MAX_NICKNAME_LENGTH}"
UNKNOWN_ERROR = "Unknown error, please support administrator by: Telegram - @dredsss"
INVALID_TEXT = "Some of passed arguments could not be decoded to UTF-8 or correctly parsed. Retry your request."
INVALID_USER = "Invalid credentials"
USER_IS_LOGGED = "User is already logged in. Wait until original session is ended or log out."
USER_EXISTS = "This nickname is already registered."
MAX_SESSIONS = "Max amount of sessions. Log out from any session to create new one."
INVALID_TOKEN = "JWT token is invalid and could not be verified."
TOKEN_EXPIRED = "This JWT token is expired."
POST_VALIDATE_ERROR = f"Invalid title or content. Title length must be {config.POST_MIN_TITLE_LENGTH} <= x <= {config.POST_MAX_TITLE_LENGTH}. " \
                      f"Content length must be less than {config.POST_MAX_CONTENT_LENGTH} symbols."
LIMIT_VALIDATE_ERROR = f"Incorrect limit. It must be 1 <= x <= {config.POST_MAX_RECEIVE_LIMIT}"
INVALID_ID = "Invalid ID. ID must be bigger than 0"
POST_DOES_NOT_EXIST = "Post of this ID does not exist"
IP_VALIDATE_ERROR = "IP validation was not passed. Token is now expired."
NO_ACCESS = "You don't have permission to modify/delete this post since you are not its author"
NO_ACCESS_RATE = "You cannot like or dislike your own posts"
RENEW_BEFORE_LOGIN = "You cannot renew token until you log in"

# FastAPI messages
FASTAPI_TITLE = "Social Network by @dredsss"
FASTAPI_DESCRIPTION = """# Simple FastAPI blog implementation
### Author: telegram @dredsss

Authorization system is based on JWT tokens, read method documentations"""
FASTAPI_VERSION = "1.0"
