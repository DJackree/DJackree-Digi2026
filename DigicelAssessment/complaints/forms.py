"""Complaint forms for Phase 2 (backend + minimal templates)."""

from __future__ import annotations

from django import forms
from django.contrib.auth.models import User

from accounts.models import UserProfile
from complaints.models import Complaint


MIN_DESCRIPTION_LEN = 20


class ComplaintCreateForm(forms.Form):
    category = forms.ChoiceField(
        choices=Complaint.Category.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Describe your issue (be specific)",
            }
        ),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.is_bound:
            for fname, field in self.fields.items():
                if fname in self.errors:
                    wcls = field.widget.attrs.get("class", "")
                    field.widget.attrs["class"] = f"{wcls} is-invalid".strip()

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < MIN_DESCRIPTION_LEN:
            raise forms.ValidationError(
                f"Please enter at least {MIN_DESCRIPTION_LEN} characters."
            )
        return text


class ComplaintStatusUpdateForm(forms.Form):
    status = forms.ChoiceField(
        choices=Complaint.Status.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 3, "placeholder": "Optional internal note"}
        ),
    )

    def __init__(
        self,
        *args,
        allowed_statuses: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        choices = Complaint.Status.choices
        if allowed_statuses is not None:
            allowed_set = set(allowed_statuses)
            choices = [(v, lbl) for v, lbl in Complaint.Status.choices if v in allowed_set]
        self.fields["status"].choices = choices


class ComplaintNoteForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Internal note (not visible to customer)",
            }
        ),
    )

    def clean_body(self):
        text = self.cleaned_data["body"].strip()
        if not text:
            raise forms.ValidationError("Note cannot be empty.")
        return text


class EscalationForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Why is this being escalated?",
            }
        ),
    )

    def clean_reason(self):
        text = self.cleaned_data["reason"].strip()
        if not text:
            raise forms.ValidationError("Escalation reason is required.")
        return text


class ComplaintAssignmentForm(forms.Form):
    agent = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select an agent",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["agent"].queryset = User.objects.filter(
            profile__role=UserProfile.Role.AGENT,
        ).order_by("username")


class AdminStatusOverrideForm(forms.Form):
    status = forms.ChoiceField(
        choices=Complaint.Status.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 3, "placeholder": "Optional audit note"}
        ),
    )
