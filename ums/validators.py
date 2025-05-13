import re
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError


@deconstructible
class CustomUsernameValidator(object):
    message = _("Phone number must start with [0] and must be 11 digits")

    def __call__(self, value):
        if not (value.startswith("0") and len(value) == 11):
            raise ValidationError(self.message, code="invalid_username")


custom_usename_validator = [CustomUsernameValidator()]
