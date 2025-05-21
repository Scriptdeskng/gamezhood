from .base import *


DEBUG = True

ALLOWED_HOSTS = []


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT")
EMAIL_USE_TLS = config("EMAIL_USE_TLS")


DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")


EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")


ADMINS = (("Game Splash Support", "hello@zamari.tv"),)


# CELERY related settings
BROKER_URL = "amqp://localhost"
# CELERY_RESULT_BACKEND = 'amqp://'
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Lagos"


# AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
# AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")

# AWS_S3_FILE_OVERWRITE = False
# AWS_DEFAULT_ACL = None
# AWS_S3_REGION_NAME = "us-east-1"
# DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"


DO_SPACES_ACCESS_KEY_ID = config("DO_SPACE_ACCESS_KEY")
DO_SPACES_SECRET_ACCESS_KEY = config("DO_SPACE_SECRET_KEY")
DO_SPACES_BUCKET_NAME = "gamezhood-bucket"
DO_SPACES_REGION_NAME = "fra1"
DO_SPACES_ENDPOINT_URL = "https://fra1.digitaloceanspaces.com"


AWS_ACCESS_KEY_ID = DO_SPACES_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = DO_SPACES_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME = DO_SPACES_BUCKET_NAME
AWS_S3_REGION_NAME = DO_SPACES_REGION_NAME
AWS_S3_ENDPOINT_URL = DO_SPACES_ENDPOINT_URL
AWS_S3_SIGNATURE_VERSION = "s3v4"


AWS_S3_CUSTOM_DOMAIN = (
    f"{DO_SPACES_BUCKET_NAME}.{DO_SPACES_REGION_NAME}.digitaloceanspaces.com"
)

AWS_DEFAULT_ACL = "public-read"

# Ensure file paths are correct
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

DEFAULT_FILE_STORAGE = "config.settings.storage_backends.MediaStorage"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
