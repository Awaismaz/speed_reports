from django.contrib.auth.password_validation import UserAttributeSimilarityValidator
from django.core.exceptions import ValidationError

class CustomAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def get_help_text(self):
        return 'Avoid using your name or other personal information as your password.'
    
    def validate(self, password, user=None):
        super().validate(password, user)
        if self.get_help_text() in self.error_list:
            raise ValidationError(
                'Avoid using your name or other personal information as your password.',
                code='password_too_similar',
            )
