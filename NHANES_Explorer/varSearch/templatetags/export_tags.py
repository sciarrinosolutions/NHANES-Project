import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def tojson(value):
    """
    Serialize a Python value to a JSON string safe for inline use in
    a <script> block.  Escapes </script> to prevent XSS.
    """
    serialized = json.dumps(value, ensure_ascii=False)
    # Prevent </script> from closing the script tag prematurely
    serialized = serialized.replace('</script>', r'<\/script>')
    return mark_safe(serialized)


@register.filter
def dict_items(value):
    """Return .items() for a dict, safe to use in templates."""
    if isinstance(value, dict):
        return value.items()
    return []
