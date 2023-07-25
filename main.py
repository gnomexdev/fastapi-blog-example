from builtins import print as _print
from fastapi import FastAPI, HTTPException, Request
import auth as _auth
import config
import messages
import utils
from database import Database, User, Post, FetchStatus, AddStatus, RateStatus, EditStatus
import fastapi_response_models as response_models
# import fastapi_request_models as request_models

# TODO prevent DOS by limiting requests per minute
if config.DEBUG:
	print = lambda *args, **kwargs: _print('\033[96m debug *', *args, '\033[0m', **kwargs)
else:
	print = lambda *args, **kwargs: None


print("Initializing app...")
app = FastAPI(title=messages.FASTAPI_TITLE, description=messages.FASTAPI_DESCRIPTION, version=messages.FASTAPI_VERSION)

db: Database | None = None

print("Initializing auth module...")
auth = _auth.Auth()

logged_users: dict[str, list[str]] = {}  # Nickname: jwt token
token_ip: dict[str, str] = {}


# UTIL token validator
async def token_validation(jwt_token: str, request: Request) -> tuple[dict | HTTPException, bool]:
	"""Returns either payload from a token or an exception to raise.
	If second return boolean is False, then token is expired or broken and
	then first element of tuple is exception"""
	if await db.check_token_expired(jwt_token):
		raise HTTPException(400, messages.TOKEN_EXPIRED)

	client_host = request.client.host

	payload, decode_status = auth.decode_token(jwt_token)

	if decode_status == _auth.DecodeStatus.OK:
		if config.VALIDATE_IP_OF_SESSION:  # Validating IP if config says so
			print(client_host, 'validating ip')
			if jwt_token not in token_ip:
				token_ip[jwt_token] = client_host
			else:
				if client_host != token_ip[jwt_token]:
					await db.expire_token(jwt_token)  # expiring token that got exposed
					raise HTTPException(400, messages.IP_VALIDATE_ERROR)

		return payload, True
	elif decode_status == _auth.DecodeStatus.SIGN_EXPIRED:
		# Since token is already expired no need to check anything, just raising exception
		# Now we just clean all expired tokens from the db while we get our async time
		await db.clean_expired_tokens()
		return HTTPException(400, messages.TOKEN_EXPIRED), False
	elif decode_status == _auth.DecodeStatus.INVALID_TOKEN:
		return HTTPException(400, messages.INVALID_TOKEN), False
	else:
		print(f"token_validation exception, jwt_token: {jwt_token}; client host: {client_host}; decode_status {decode_status}")
		return HTTPException(405, messages.UNKNOWN_ERROR), False


# =====================================================================================
# ================================SESSION MANIPULATIONS================================
# =====================================================================================
@app.post("/account/singup", response_model=response_models.SignUp, status_code=201)
async def signup(nickname: str, password: str):
	"""Sign up for an account with nickname and password.
	Returns JWT token (jwt_token). It is used to make new posts, like and dislike posts"""
	if not utils.check_nickname(nickname):
		raise HTTPException(400, "Invalid nickname symbols")

	_, fetch_status = await db.get_user(nickname)

	if fetch_status == FetchStatus.OK or nickname in logged_users:
		raise HTTPException(403, messages.USER_EXISTS)

	salt = utils.generate_hash_salt()
	password_ = utils.password_to_hash(password, salt)

	user = User(nickname=nickname, password=password_, salt=salt)

	res = await db.add_user(user)
	print(f"added user; nick: {nickname}; password {password_}; salt {salt}")

	if res == AddStatus.OK:
		token = auth.generate_jwt_token_for_nickname(nickname)
		if nickname not in logged_users:
			logged_users[nickname] = [token]
		else:
			logged_users[nickname].append(token)
		return response_models.SignUp(jwt_token=token)
	else:
		raise HTTPException(405, messages.UNKNOWN_ERROR)


@app.post("/account/login", response_model=response_models.LogIn, status_code=201)
async def login(nickname: str, password: str):
	"""Login to account using nickname and password"""
	if not utils.check_nickname(nickname):
		raise HTTPException(400, messages.INVALID_NICK)

	if nickname in logged_users and logged_users[nickname].__len__() == config.MAX_SESSIONS_ALLOWED:
		raise HTTPException(403, messages.MAX_SESSIONS)

	user, fetch_status = await db.get_user(nickname)

	if fetch_status == FetchStatus.OK:
		# Checking password NOTE
		user_pwd_hash = user.password
		received_pwd_has = utils.password_to_hash(password, user.salt)

		if not received_pwd_has:
			raise HTTPException(400, messages.INVALID_TEXT)

		if received_pwd_has == user_pwd_hash:
			token = auth.generate_jwt_token_for_nickname(nickname)

			if nickname not in logged_users:
				logged_users[nickname] = [token]
			else:
				logged_users[nickname].append(token)

			return response_models.LogIn(jwt_token=token)
		else:
			raise HTTPException(403, messages.INVALID_USER)
	elif fetch_status == FetchStatus.UNSUPPORTED_SYMBOLS:
		raise HTTPException(400, messages.INVALID_NICK)
	elif fetch_status == FetchStatus.USER_DOES_NOT_EXIST:
		raise HTTPException(403, messages.INVALID_USER)
	else:
		raise HTTPException(405, messages.UNKNOWN_ERROR)  # TODO err ids for debugging


@app.get("/account/renew_token")
async def renew_JWT_token(jwt_token: str, request: Request) -> response_models.Renew:
	"""Renew JWT token in case they are close to be expired.
	Returned token will be your new token, and the one that was passed as argument will be expired."""
	payload, status = await token_validation(jwt_token, request)
	if not status: raise payload

	nick = payload["nickname"]
	client_host = request.client.host

	token = auth.generate_jwt_token_for_nickname(nick)

	await db.expire_token(jwt_token)

	if nick not in logged_users:
		logged_users[nick] = [token]
	else:
		logged_users[nick].append(token)

	return response_models.Renew(jwt_token=token)


@app.get("/account/logout", status_code=201, response_model=response_models.LogOut)
async def logout(jwt_token: str, request: Request):
	"""Logout from session, token will be considered expired by server"""
	payload, status = await token_validation(jwt_token, request)
	if not status: raise payload
	await db.expire_token(jwt_token)

	nick = payload["nickname"]

	if nick in logged_users:
		logged_users[nick].pop(logged_users[nick].index(jwt_token))

	return response_models.LogOut(status=response_models.LogOut.BasicStatus.OK)


# =====================================================================================
# =====================================================================================
# =====================================================================================


# =====================================================================================
# ======================================POSTS==========================================
# =====================================================================================
@app.post("/posts/new", response_model=response_models.PostCreated)
async def posts_new(jwt_token: str, title: str, content: str, request: Request):
	"""Create new post as a user"""
	payload, status = await token_validation(jwt_token, request)
	if not status: raise payload

	if not utils.check_post(title, content):
		raise HTTPException(400, messages.POST_VALIDATE_ERROR)

	nickname = payload["nickname"]
	user, fetch_status = await db.get_user(nickname)

	if fetch_status == FetchStatus.OK:
		post_id, status = await db.add_post(user, title, content)
		if status == AddStatus.OK:
			return response_models.PostCreated(post_id=post_id)
		else:
			raise HTTPException(400, messages.INVALID_TEXT)
	else:
		raise HTTPException(400, messages.UNKNOWN_ERROR)  # Cuz weve already validated token no chance that nickname does not exist


@app.get("/posts/get_all")
async def posts_get_all(limit: int | None = config.POST_MAX_RECEIVE_LIMIT) -> list[Post]:
	"""Get all newest posts. `limit` argument limits amount of posts fetched (default is set by server config)"""
	# This method does not require validation, cuz posts are public to fetch

	posts, fetch_status = await db.get_posts(limit=limit)

	if fetch_status != FetchStatus.OK:
		raise HTTPException(405, messages.UNKNOWN_ERROR)

	return posts


@app.get("/posts/get")
async def posts_get(id_: int) -> Post:
	"""Get post by its id"""
	post, fetch_status = await db.get_post(id_)
	if fetch_status == FetchStatus.INCORRECT_ID:
		raise HTTPException(400, messages.INVALID_ID)
	elif fetch_status == FetchStatus.POST_DOES_NOT_EXIST:
		raise HTTPException(400, messages.POST_DOES_NOT_EXIST)

	return post


async def rate_post(jwt_token: str, post_id: int, is_like: bool, request: Request):
	"""Like post as user"""
	payload, status = await token_validation(jwt_token, request)
	if not status: raise payload

	rate_result = await db.set_rate(post_id, payload["nickname"], is_like)

	if rate_result == RateStatus.NO_POST:
		raise HTTPException(400, messages.POST_DOES_NOT_EXIST)
	elif rate_result == RateStatus.NO_ACCESS:
		raise HTTPException(403, messages.NO_ACCESS_RATE)
	elif rate_result == RateStatus.ERROR:
		raise HTTPException(405, messages.UNKNOWN_ERROR)

	return response_models.Status(status=response_models.Status.BasicStatus.OK)


@app.post("/posts/like", response_model=response_models.Status)
async def like_post(jwt_token: str, post_id: int, request: Request):
	"""Like a post"""
	return await rate_post(jwt_token, post_id, True, request)


@app.post("/posts/dislike", response_model=response_models.Status)
async def dislike_post(jwt_token: str, post_id: int, request: Request):
	"""Dislike a post"""
	return await rate_post(jwt_token, post_id, False, request)


@app.post("/posts/remove_rate", response_model=response_models.Status)
async def remove_rate_from_post(jwt_token: str, post_id: int, request: Request):
	"""Remove any like or dislike you have given the post"""
	payload, status = await token_validation(jwt_token, request)
	if not status: raise payload

	rate_result = await db.unset_rate(post_id, payload["nickname"])

	if rate_result == RateStatus.NO_POST:
		raise HTTPException(400, messages.POST_DOES_NOT_EXIST)
	elif rate_result == RateStatus.NO_ACCESS:
		raise HTTPException(403, messages.NO_ACCESS_RATE)
	elif rate_result == RateStatus.ERROR:
		raise HTTPException(405, messages.UNKNOWN_ERROR)

	return response_models.Status(status=response_models.Status.BasicStatus.OK)


@app.post("/posts/edit", response_model=response_models.Status)
async def edit_post(jwt_token: str, post_id: int, request: Request, new_title: str = None, new_content: str = None):
	"""Edit your post. `new_title` and `new_content` are optional by themselves, but at least one of them must be set"""
	payload, status = await token_validation(jwt_token, request)
	if not status: raise payload

	if not new_title and not new_content:
		return response_models.Status(status=response_models.Status.BasicStatus.ERROR, details="At least specify new_title or new_content")

	await db.edit_post(post_id, payload["nickname"], new_title=new_title, new_content=new_content)
	return response_models.Status(status=response_models.Status.BasicStatus.OK)


@app.post("/posts/delete", response_model=response_models.Status)
async def delete_post(jwt_token: str, post_id: int, request: Request):
	"""Delete your post"""
	payload, status = await token_validation(jwt_token, request)
	if not status: raise payload

	if not utils.check_id(post_id):
		raise HTTPException(400, messages.INVALID_ID)

	status = await db.delete_post(post_id, payload["nickname"])

	if status == EditStatus.OK:
		return response_models.Status(status=response_models.Status.BasicStatus.OK)
	elif status == EditStatus.NO_POST:
		return HTTPException(400, messages.POST_DOES_NOT_EXIST)
	elif status == EditStatus.NO_ACCESS:
		return HTTPException(403, messages.NO_ACCESS)
	else:
		raise HTTPException(400, messages.UNKNOWN_ERROR)


@app.on_event("startup")
async def startup():
	global db
	db = Database()
	print("initializing db...")
	await db.init_database()
	print("initialized db")


@app.on_event("shutdown")
async def shutdown():
	print("closing")
	await db.close()
