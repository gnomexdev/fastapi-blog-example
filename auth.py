import enum
import jwt
import config
import os
import time
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from typing import Any


class DecodeStatus(enum.Enum):
	OK = 1
	SIGN_EXPIRED = 2
	INVALID_TOKEN = 3


class Auth:
	key: rsa.RSAPrivateKey

	def __generate_new_keypair(self):
		# Generating new key
		self.key = rsa.generate_private_key(public_exponent=65537, key_size=config.KEYPAIR_SIZE)

	def __save_key_to_disk(self):
		# Saving freshly generated key
		with open(config.KEYPAIR_FILENAME, "wb") as fh:
			fh.write(self.key.private_bytes(
				encoding=serialization.Encoding.PEM,
				format=serialization.PrivateFormat.PKCS8,
				encryption_algorithm=serialization.NoEncryption()
			))

	def __load_keypair(self):
		with open(config.KEYPAIR_FILENAME, "rb") as fh:
			self.key = serialization.load_pem_private_key(
				fh.read(),
				password=None
			)

	def __init__(self):
		assert os.access(os.path.split(config.KEYPAIR_FILENAME)[0], os.W_OK | os.R_OK | os.F_OK), \
			"Key directory is unavailable"

		if os.access(config.KEYPAIR_FILENAME, os.F_OK):
			self.__load_keypair()
		else:
			self.__generate_new_keypair()
			self.__save_key_to_disk()

	def generate_jwt_token(self, payload: dict):
		"""Generate new JWT token"""
		payload_ = payload
		payload_["iat"] = time.time()
		if config.SESSION_LIFESPAN_MINUTES:
			payload_["exp"] = time.time() + config.SESSION_LIFESPAN_MINUTES * 60
		return jwt.encode(
			payload=payload_,
			key=self.key,
			algorithm="RS256"  # We are using RS256 in case we will need to make our service connectible
		)

	def generate_jwt_token_for_nickname(self, nickname: str):
		return self.generate_jwt_token({"nickname": nickname})

	def decode_token(self, token) -> tuple[dict[str, Any] | None, DecodeStatus]:
		try:
			return jwt.decode(token, self.key.public_key(), algorithms=["RS256"], verify=True), DecodeStatus.OK
		except jwt.exceptions.InvalidSignatureError:
			return None, DecodeStatus.INVALID_TOKEN  # TODO mb check some metrics to prevent brute forcing idk
		except jwt.exceptions.DecodeError:
			return None, DecodeStatus.INVALID_TOKEN
		except jwt.exceptions.ExpiredSignatureError:
			return None, DecodeStatus.SIGN_EXPIRED
