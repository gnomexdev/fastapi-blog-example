import aiosqlite as sq3
from builtins import print as _print
import sqlite3 as _sq3
import config
import dataclasses
import enum
import utils
import json
import time
from typing import Tuple


if config.DEBUG:
	print = lambda *args, **kwargs: _print('\033[96m debug *', *args, '\033[0m', **kwargs)
else:
	print = lambda *args, **kwargs: None


@dataclasses.dataclass
class User:
	"""
	password must be a SHA512 hash
	"""
	nickname: str
	password: bytes  # SHA512 Hash
	salt: bytes = None


@dataclasses.dataclass
class Post:
	id_: int
	author_nickname: str
	title: str
	content: str
	posted_ts: int
	liked_nicknames: list[str]
	disliked_nicknames: list[str]


class AddStatus(enum.Enum):
	OK = 1
	UNKNOWN_ERROR = 2
	NICKNAME_TOO_LONG = 3
	USER_EXISTS = 4
	UNSUPPORTED_SYMBOLS = 5
	INVALID_POST = 6


class FetchStatus(enum.Enum):
	OK = 1
	UNSUPPORTED_SYMBOLS = 2
	USER_DOES_NOT_EXIST = 3
	POST_DOES_NOT_EXIST = 4
	UNKNOWN_ERROR = 5
	INCORRECT_LIMIT = 6
	INCORRECT_ID = 7


class RateStatus(enum.Enum):
	OK = 1
	NO_POST = 2
	ERROR = 3
	NO_ACCESS = 4


class EditStatus(enum.Enum):
	OK = 1
	NO_POST = 2
	INVALID_POST = 3
	NO_ACCESS = 4
	INCORRECT_ID = 5
	ERROR = 6


class Database:
	db = sq3.Connection
	__initialized = False

	async def init_database(self):
		if self.__initialized:
			return

		self.db = await sq3.connect(config.DB_FILENAME, detect_types=_sq3.PARSE_DECLTYPES | _sq3.PARSE_COLNAMES, isolation_level=None)

		# Creating users table
		await (await self.db.execute(
			"CREATE TABLE IF NOT EXISTS users(nickname TEXT UNIQUE, password BLOB, salt BLOB)"
		)).close()

		await (await self.db.execute(
			"CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, author_nickname TEXT NOT NULL, title TEXT, content TEXT, ts_posted INTEGER)"
		)).close()

		await (await self.db.execute(
			"CREATE TABLE IF NOT EXISTS post_rates(post_id INTEGER NOT NULL, is_like BOOL, nickname TEXT)"
		)).close()

		await (await self.db.execute(
			"CREATE TABLE IF NOT EXISTS expired_tokens(token TEXT UNIQUE NOT NULL, expire_ts INTEGER NOT NULL)"
		)).close()

		self.__initialized = True

	def __check_initialized(self):
		assert self.__initialized, "Database is not initialized, run init_database() first"

	async def check_token_expired(self, token: str) -> tuple[int, int] | None:
		"""Returns None if token is not expired and (id, timestamp) if it is. This is my JWT logout implementation"""
		c = await self.db.cursor()
		await c.execute("SELECT expire_ts FROM expired_tokens WHERE token = ?", (token,))
		d = await c.fetchone()
		await c.close()

		return None or d

	async def expire_token(self, token: str):
		await (await self.db.execute("INSERT OR IGNORE INTO expired_tokens(token, expire_ts) VALUES (?, ?)", (token, time.time()))).close()

	async def clean_expired_tokens(self):
		await (await self.db.execute("DELETE FROM expired_tokens WHERE expire_ts <= ?", (time.time(),))).close()

	async def add_user(self, user: User) -> AddStatus:
		self.__check_initialized()

		if not utils.check_nickname(user.nickname):
			return AddStatus.NICKNAME_TOO_LONG

		try:
			await (await self.db.execute("INSERT INTO users(nickname, password, salt) VALUES (?, ?, ?)", (user.nickname, user.password, user.salt))).close()
			return AddStatus.OK
		except sq3.IntegrityError:  # User exists, unique test failed
			return AddStatus.USER_EXISTS
		except sq3.Error:
			return AddStatus.UNKNOWN_ERROR

	async def get_user(self, nickname: str) -> Tuple[User | None, FetchStatus]:
		self.__check_initialized()

		try:
			c = await self.db.cursor()
			await c.execute("SELECT nickname, password, salt FROM users WHERE nickname = ?", (nickname,))
		except sq3.ProgrammingError:
			return None, FetchStatus.UNSUPPORTED_SYMBOLS

		data = await c.fetchone()
		await c.close()

		if not data:
			return None, FetchStatus.USER_DOES_NOT_EXIST

		return User(nickname=data[0], password=data[1], salt=data[2]), FetchStatus.OK

	async def add_post(self, author: User, title: str, content: str) -> tuple[int | None, AddStatus]:
		"""Returns added post_id and addstatus if successful. If err occures, first value of return tuple will be None"""
		self.__check_initialized()
		if not utils.check_post(title, content):
			return None, AddStatus.INVALID_POST
		try:
			c = await self.db.cursor()
			current_time = time.time().__round__()
			await c.execute("SELECT MAX(id) FROM posts")
			max_id = await c.fetchone()
			if max_id[0]:
				print(max_id)
				next_post_id = max_id[0] + 1
			else:
				next_post_id = 1

			await c.execute("INSERT INTO posts(author_nickname, title, content, ts_posted) VALUES (?, ?, ?, ?)", (author.nickname, title, content, current_time))
			await c.close()
		except sq3.ProgrammingError:
			return None, AddStatus.UNSUPPORTED_SYMBOLS
		except sq3.Error:
			return None, AddStatus.UNKNOWN_ERROR

		return next_post_id, AddStatus.OK

	async def _get_post_rates(self, id_: int, nickname: str = None) -> tuple[list[str], list[str]] | None:
		if not utils.check_id(id_):
			print("bad id")
			return

		c = await self.db.cursor()
		if not nickname:
			await c.execute("SELECT is_like, nickname FROM post_rates WHERE post_id = ?", (id_,))  # fetching all rates for this post
		else:
			await c.execute("SELECT is_like, nickname FROM post_rates WHERE post_id = ? AND nickname = ?", (id_, nickname))

		rates = await c.fetchall()

		await c.close()

		like_nicknames = []
		dislike_nicknames = []
		for is_like, rate_nickname in rates:
			if is_like:
				like_nicknames.append(rate_nickname)
			else:
				dislike_nicknames.append(rate_nickname)

		return like_nicknames, dislike_nicknames

	async def get_post(self, id_: int) -> Tuple[Post | None, FetchStatus]:
		self.__check_initialized()

		if not utils.check_id(id_):
			return None, FetchStatus.INCORRECT_ID

		try:
			c = await self.db.cursor()

			await c.execute("SELECT author_nickname, title, content, ts_posted FROM posts WHERE id = ?", (id_,))

			data = await c.fetchone()

			await c.close()

			if not data:
				return None, FetchStatus.POST_DOES_NOT_EXIST

			like_nicknames, dislike_nicknames = await self._get_post_rates(id_)

			return Post(id_, data[0], data[1], data[2], data[3], like_nicknames, dislike_nicknames), FetchStatus.OK
		except sq3.ProgrammingError:
			return None, FetchStatus.UNSUPPORTED_SYMBOLS
		except sq3.Error:
			return None, FetchStatus.UNKNOWN_ERROR

	async def get_posts(self, limit: int | None = config.POST_MAX_RECEIVE_LIMIT) -> tuple[list[Post] | None, FetchStatus]:
		if limit and not 1 <= limit <= config.POST_MAX_RECEIVE_LIMIT:
			return None, FetchStatus.INCORRECT_LIMIT

		c = await self.db.cursor()
		if limit:
			await c.execute("SELECT * FROM posts ORDER BY id DESC LIMIT ?", (limit,))
		else:
			await c.execute("SELECT * FROM posts ORDER BY id DESC")

		posts = []

		for data in await c.fetchall():
			print(data)
			rates = await self._get_post_rates(data[0])
			print(rates)
			like_nicknames, dislike_nicknames = rates  # NOTE
			posts.append(Post(data[0], data[1], data[2], data[3], data[4], like_nicknames, dislike_nicknames))
		await c.close()

		return posts, FetchStatus.OK

	async def edit_post(self, post_id: int, nickname: str, new_title: str = None, new_content: str = None) -> EditStatus:
		if not new_title and not new_content:
			return EditStatus.OK

		if not utils.check_post(new_title, new_content):
			return EditStatus.INVALID_POST

		if not utils.check_id(post_id):
			return EditStatus.INCORRECT_ID

		post, fetch_status = await self.get_post(post_id)
		if fetch_status != FetchStatus.OK:
			return EditStatus.NO_POST

		if post.author_nickname != nickname:
			return EditStatus.NO_ACCESS

		c = await self.db.cursor()
		if new_title and new_content:
			await c.execute("UPDATE posts SET title = ?, content = ? WHERE id = ?", (new_title, new_content, post_id))
		elif new_title:
			await c.execute("UPDATE posts SET title = ? WHERE id = ?", (new_title, post_id))
		else:
			await c.execute("UPDATE posts SET content = ? WHERE id = ?", (new_content, post_id))  # I know i could do this
			# easier way, but im too cautious ya know ;)
		await c.close()

		return EditStatus.OK

	async def delete_post(self, post_id: int, nickname: str) -> EditStatus:
		if not utils.check_id(post_id):
			return EditStatus.INCORRECT_ID

		post, fetch_status = await self.get_post(post_id)
		if fetch_status != FetchStatus.OK:
			return EditStatus.NO_POST

		if post.author_nickname != nickname:
			return EditStatus.NO_ACCESS

		c = await self.db.cursor()
		await c.execute("DELETE FROM posts WHERE id = ?", (post_id, ))
		await c.execute("DELETE FROM post_rates WHERE post_id = ?", (post_id,))
		await c.close()

		return EditStatus.OK

	async def set_rate(self, post_id: int, nickname: str, is_like: bool) -> RateStatus:
		post, fetch_status = await self.get_post(post_id)
		if fetch_status == FetchStatus.POST_DOES_NOT_EXIST:
			return RateStatus.NO_POST
		elif fetch_status == FetchStatus.UNKNOWN_ERROR:
			return RateStatus.ERROR

		if post.author_nickname == nickname:
			return RateStatus.NO_ACCESS

		c = await self.db.cursor()

		rates = await self._get_post_rates(post_id, nickname)

		if not rates[0] and not rates[1]:  # User did not like or dislike this post
			await c.execute("INSERT INTO post_rates(post_id, is_like, nickname) VALUES (?, ?, ?)", (post_id, is_like, nickname))
		else:
			await c.execute("UPDATE post_rates SET is_like = ? WHERE post_id = ? AND nickname = ?",  # Updating his rate
			                (is_like, post_id, nickname))
		await c.close()

		return RateStatus.OK

	async def unset_rate(self, post_id: int, nickname: str) -> RateStatus:
		post, fetch_status = await self.get_post(post_id)
		if fetch_status == FetchStatus.POST_DOES_NOT_EXIST:
			return RateStatus.NO_POST
		elif fetch_status == FetchStatus.UNKNOWN_ERROR:
			return RateStatus.ERROR

		if post.author_nickname == nickname:
			return RateStatus.NO_ACCESS

		c = await self.db.cursor()
		await c.execute("DELETE FROM post_rates WHERE post_id = ? AND nickname = ?", (post_id, nickname))
		await c.close()

		return RateStatus.OK

	async def close(self):
		await self.db.close()
