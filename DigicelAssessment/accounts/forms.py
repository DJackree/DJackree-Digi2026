from django.contrib.auth.forms import AuthenticationForm


class BootstrapAuthenticationForm(AuthenticationForm):
    """Adds Bootstrap form-control classes for Phase 3 templates."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for name in ("username", "password"):
            field = self.fields[name]
            widget = field.widget
            attrs = widget.attrs
            existing = attrs.get("class", "")
            merged = f"{existing} form-control".strip()
            attrs["class"] = merged
            if name == "username":
                attrs.setdefault("autocomplete", "username")
            if name == "password":
                attrs.setdefault("autocomplete", "current-password")

        if self.is_bound:
            for fname, field in self.fields.items():
                if fname in self.errors:
                    fe = field.widget.attrs.get("class", "")
                    field.widget.attrs["class"] = (f"{fe} is-invalid").strip()
