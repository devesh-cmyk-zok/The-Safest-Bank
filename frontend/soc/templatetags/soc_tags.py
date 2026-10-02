from django import template

from soc.services import inr as _inr

register = template.Library()


@register.filter
def inr(value):
    return _inr(value or 0)


@register.filter
def pct(value, digits=1):
    return f"{float(value or 0) * 100:.{int(digits)}f}%"


@register.filter
def duration(seconds):
    """93.5 -> '1m 34s'; None -> '—'."""
    if seconds is None:
        return "—"
    s = int(round(seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s // 3600}h {(s % 3600) // 60:02d}m"
