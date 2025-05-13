from storages.backends.s3boto3 import S3Boto3Storage
import boto3


class MediaStorage(S3Boto3Storage):
    location = ""
    file_overwrite = False
