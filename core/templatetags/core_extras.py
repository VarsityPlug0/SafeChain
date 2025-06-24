from django import template
import random

register = template.Library()

@register.filter
def random_color(counter):
    """Generate a random color based on the counter value"""
    colors = [
        '#2563eb',  # blue
        '#7c3aed',  # purple
        '#059669',  # green
        '#dc2626',  # red
        '#d97706',  # orange
        '#0891b2',  # cyan
        '#4f46e5',  # indigo
        '#db2777',  # pink
        '#65a30d',  # lime
        '#9333ea',  # violet
    ]
    return colors[counter % len(colors)] 