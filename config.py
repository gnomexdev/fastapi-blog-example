DEBUG = True  # If true some specific runtime debug logs will print into console

# RSA key filepath
KEYPAIR_FILENAME = "./key.pem"  # Relative/Absolute path, if file is located in working directory use ./filename
# Size of RSA key, do not change if you don't know what you're doing
KEYPAIR_SIZE = 2048
# SQlite3 database filename, relative or absolute path
DB_FILENAME = "db.sqlite3"


# DB config #
MAX_NICKNAME_LENGTH = 16  # Must be set
MIN_NICKNAME_LENGTH = 4  # Must be set
# # # # # # #


# Session config #
SESSION_LIFESPAN_MINUTES = 30  # If None, session is infinite until user logs out, else pass lifespan in minutes
MAX_SESSIONS_ALLOWED = 1  # Max sessions that can be opened for 1 nickname
VALIDATE_IP_OF_SESSION = False  # Token instantly expires in case server receive request with this token
# but from IP different from which token was requested from originally. Recommended: False
# # # # # # # # # #


# Posts config #
POST_MAX_CONTENT_LENGTH = 500  # Max length of post content (body)
POST_MIN_TITLE_LENGTH = 3  # Min length of post title
POST_MAX_TITLE_LENGTH = 50  # Max length of post title
POST_MAX_RECEIVE_LIMIT = 400  # Max amount of posts that server will fetch from the top
# # # # # # # #
