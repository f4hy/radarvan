"""Whole-object S3 reads and writes, addressed by ``s3://bucket/key`` URI."""

from functools import cache
from typing import Any, NamedTuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Above the widest S3 fan-out (admin backfills run 20 worker threads); past the
# pool size urllib3 drops connections and every extra request pays a new TLS
# handshake.
_MAX_POOL_CONNECTIONS = 32


class S3Location(NamedTuple):
    bucket: str
    key: str


def parse_uri(uri: str) -> S3Location:
    # Scheme optional: s3fs accepted bare "bucket/key", so stored URIs may too.
    bucket, _, key = uri.removeprefix("s3://").partition("/")
    if not bucket or not key:
        raise ValueError(f"not an S3 object URI: {uri!r}")
    return S3Location(bucket, key)


class S3Store:
    def __init__(self, client: Any) -> None:
        # Typed Any because the precise S3Client type lives in boto3-stubs
        # (dev-only) and TYPE_CHECKING imports are banned here.
        self.client = client

    def read_bytes(self, uri: str) -> bytes:
        loc = parse_uri(uri)
        try:
            response = self.client.get_object(Bucket=loc.bucket, Key=loc.key)
        except self.client.exceptions.NoSuchKey as e:
            raise FileNotFoundError(uri) from e
        body: bytes = response["Body"].read()
        return body

    def read_text(self, uri: str) -> str:
        return self.read_bytes(uri).decode()

    def write_bytes(self, uri: str, data: bytes) -> None:
        loc = parse_uri(uri)
        self.client.put_object(Bucket=loc.bucket, Key=loc.key, Body=data)

    def write_text(self, uri: str, text: str) -> None:
        self.write_bytes(uri, text.encode())

    def exists(self, uri: str) -> bool:
        loc = parse_uri(uri)
        try:
            self.client.head_object(Bucket=loc.bucket, Key=loc.key)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True

    def presigned_get_url(
        self, uri: str, expires_in: int, save_as: str | None = None
    ) -> str:
        loc = parse_uri(uri)
        params = {"Bucket": loc.bucket, "Key": loc.key}
        if save_as is not None:
            params["ResponseContentDisposition"] = f'attachment; filename="{save_as}"'
        url = self.client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )
        return str(url)


@cache
def get_store() -> S3Store:
    # Client construction (credential/endpoint resolution) is expensive and the
    # client is thread-safe; build it once.
    return S3Store(
        boto3.client(
            "s3",
            region_name="us-east-2",
            config=Config(
                signature_version="s3v4", max_pool_connections=_MAX_POOL_CONNECTIONS
            ),
        )
    )
