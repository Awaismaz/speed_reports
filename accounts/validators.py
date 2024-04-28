from django.contrib.auth.password_validation import UserAttributeSimilarityValidator
from django.core.exceptions import ValidationError

class CustomAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError as e:
            # Check if the default error message is in the exception
            if 'The password is too similar to the' in str(e):
                raise ValidationError(
                    'Avoid using your name or other personal information as your password.',
                    code='password_too_similar',
                )
            else:
                # If the error is not about attribute similarity, re-raise the original error
                raise e

    def get_help_text(self):
        return 'Your password should not be too similar to your other personal information.'
