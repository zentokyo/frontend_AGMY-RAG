from datetime import datetime, UTC

from aiobotocore.client import AioBaseClient
from botocore.exceptions import ClientError

from src.core.commons.exception import S3StorageException, S3FileNotFoundException
from src.core.commons.interfaces.storages.s3 import S3Storage


class MinioS3Storage(S3Storage):
    def __init__(
            self,
            bucket: str,
            client: AioBaseClient
    ):
        self._bucket = bucket
        self._client = client

    async def upload_file(self, data: bytes, filename: str) -> None:
        metadata = {
            "created": datetime.now(UTC).isoformat(),
            "original_filename": filename,
        }

        await self._client.put_object(
            Bucket=self._bucket,
            Key=filename,
            Body=data,
            ContentType="application/pdf",
            Metadata=metadata,
        )

    async def download_file(self, filename: str) -> bytes:
        if not await self.is_file_exists(filename=filename):
            raise S3FileNotFoundException(filename)

        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=filename)
        except ClientError:
            raise S3StorageException
        async with response["Body"] as stream:
            return await stream.read()

    async def is_file_exists(self, filename: str) -> bool:
        try:
            await self._client.head_object(Bucket=self._bucket, Key=filename)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise S3StorageException
        return True
