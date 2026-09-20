from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet


class OptionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        forms = [
            f for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE", False)
        ]
        if len(forms) < 4:
            raise ValidationError("A question must have at least four options.")
        if sum(bool(f.cleaned_data.get("is_correct")) for f in forms) != 1:
            raise ValidationError("Select exactly one correct option.")
