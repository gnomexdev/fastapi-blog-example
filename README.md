# Simple FastAPI blog implementation
### Author: telegram @dredsss


# How to run
### Docker build

1. `docker build -t test_job:latest .` - Build image "test_job" from Dockerfile
2. `docker run --name test_job_cont -p8000:8000 test_job:latest` - Run image in a container named "test_job"
3. To stop container, use: `docker stop test_job_cont`

### Standalone
1. Install requirements: `python -m pip install -r requirements.txt`
2. Run uvicorn server: `uvicorn --host 0.0.0.0 --port [port] main:app`
3. To stop, use Ctrl-C

# API
### Docs
ReDoc documentation is available at: __http://[host]:[port]/redoc__

OpenAPI documentation is available at __http://[host]:[port]/docs__

# Configuration
```python
DEBUG = False  # If true some specific runtime debug logs will print into console

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
SESSION_LIFESPAN_MINUTES = 30  # If None, session is infinite until user logs out, else set lifespan in minutes
MAX_SESSIONS_ALLOWED = 1  # Max sessions that can be opened for 1 nickname
VALIDATE_IP_OF_SESSION = False  # Token instantly expires in case server receives request with this token
# but from IP different from which token was requested from originally. Recommended: False
# # # # # # # # # #


# Posts config #
POST_MAX_CONTENT_LENGTH = 500
POST_MIN_TITLE_LENGTH = 3
POST_MAX_TITLE_LENGTH = 50
POST_MAX_RECEIVE_LIMIT = 400
# # # # # # # #
```

# Sessions
Depending on `SESSION_LIFESPAN_MINUTES` variable in `config.py`, generated JWT tokens
will be actual for a set period of time.

This system is pretty comfortable for developers, since you do not need to worry about
authorizing each time you connect to the API.

# Methods
## Account methods
#### /account/singup

Sign Up for an account. It accepts `nickname` and `password` arguments. Responds with `jwt_token`
<hr>

#### /account/login
Receive a JWT token, using already registered account's credentials: `nickname` and `password`

<hr>

#### /account/logout
Log out from session. It takes `jwt_token` argument, after its completion that token will be
considered expired.

<hr>

#### /account/renew_token
Create new token and expire previous. Takes `jwt_token`, responds with new `jwt_token`.

<hr>

## Posting (blogging) methods

#### /posts/get_all
Get all posts on server. Takes `limit` argument optionally,
which limits output length to this size.

<hr>

#### /posts/get
Get exact post. Takes `id_` argument, which is actually ID of a post.

<hr>

#### /posts/new
Create new post. Takes `jwt_token` for auth, `title` and `content` are post parts.

<hr>

#### /posts/like
Give post a like. Takes `jwt_token` and `post_id`. It will encount a like from this user on 
post of `post_id` ID. If user had disliked that post previously, dislike will disappear and
will be replaced by like.

<hr>

#### /posts/dislike
Dislike a post. Same as __/posts/like__, but works oppositely

<hr>

#### /posts/remove_rate
Remove any rate user has given to the post. If user has ever liked or disliked a post,
his rate will be cleared from post.

<hr>

#### /posts/edit
Edit a post. Only usable, if post was made by user, engaging this method. Takes
`jwt_token`, `post_id` and `new_title`, `new_content`.
`new_title` and `new_content` will replace original data in post.
They are both optional by themselves, but at least one of them must be set.

<hr>

#### /posts/delete
Delete a post. Only usable, if post was made by user, engaging this method. Takes
`jwt_token`, `post_id`. After usage post of this ID will be permanently deleted from database.
