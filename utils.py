import hashlib
import _hashlib
from random import choice, randbytes
from string import ascii_letters, digits
import config
import base64
import re

ALPHANUMERIC = ascii_letters + digits
_PUNCTS = "!@#$%^&*()_+{}[]\\|<>?/.,"
PUNCTUATION = ALPHANUMERIC + _PUNCTS

NICKNAME_ALLOWED_SYMBOLS_REGEX = r"^(?=.{%d,%d}$)[a-zA-Z0-9]+(?:_[a-zA-Z0-9]+)*$" % (config.MIN_NICKNAME_LENGTH, config.MAX_NICKNAME_LENGTH)
# Checks nickname to be in allowed length bounds, check its symbols to be alphanumeric + underscore
# also does not allow to put 2 underscores together or at the end/start


def generate_alphanumeric_random_string(length: int):
	assert length > 0, "`length` cannot be less than 0"

	return ''.join([choice(ALPHANUMERIC) for _ in range(length)])


def generate_printable_random_string(length: int):
	assert length > 0, "`length` cannot be less than 0"

	return ''.join([choice(PUNCTUATION) for _ in range(length)])


def generate_hash_salt():
	return randbytes(32)


def check_nickname(text: str):
	return bool(re.fullmatch(NICKNAME_ALLOWED_SYMBOLS_REGEX, text))


def password_to_hash(password: str, salt: bytes) -> bytes | None:
	"""Returns hash of password + salt"""
	return hashlib.sha512(password.encode() + salt).digest()


def check_post(title: str = None, content: str = None):
	if not title and not content:
		return False
	return (config.POST_MIN_TITLE_LENGTH <= len(title) <= config.POST_MAX_TITLE_LENGTH) \
		if title else True and (1 <= len(content) <= config.POST_MAX_CONTENT_LENGTH) if content else True


def check_id(id_: int):
	return id_ >= 1
