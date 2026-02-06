"""
DOM Parser - Extract and clean form HTML for LLM analysis

Reduces token usage by stripping unnecessary elements and keeping only
form-relevant content (inputs, labels, buttons).
"""

import re
from typing import Optional

# Heuristic field patterns - match these WITHOUT calling LLM
FIELD_PATTERNS = {
    # Contact info
    'first_name': [
        r'first.?name', r'fname', r'given.?name', r'forename'
    ],
    'last_name': [
        r'last.?name', r'lname', r'surname', r'family.?name'
    ],
    'email': [
        r'e.?mail', r'email.?address'
    ],
    'phone': [
        r'phone', r'tel', r'mobile', r'cell', r'contact.?number'
    ],
    'linkedin': [
        r'linkedin', r'linked.?in'
    ],
    'city': [
        r'\bcity\b', r'city.?name'
    ],
    'state': [
        r'\bstate\b', r'province', r'region'
    ],
    'zip': [
        r'\bzip\b', r'postal', r'post.?code'
    ],
    'address': [
        r'street', r'address.?1', r'\baddress\b'
    ],
    # Documents
    'resume': [
        r'resume', r'cv', r'curriculum'
    ],
    'cover_letter': [
        r'cover.?letter', r'motivation'
    ],
    # Work history
    'current_job_title': [
        r'job.?title', r'current.?title', r'position.?title'
    ],
    'current_company': [
        r'current.?company', r'current.?employer', r'company.?name'
    ],
    'years_experience': [
        r'years?.?(?:of)?.?experience', r'total.?experience'
    ],
}


def clean_html_for_llm(html: str, max_length: int = 8000) -> str:
    """
    Clean HTML to extract only form-relevant content.
    Dramatically reduces tokens while preserving structure.
    """
    # Remove scripts, styles, comments
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove SVG and other non-essential elements
    html = re.sub(r'<svg[^>]*>.*?</svg>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<path[^>]*/?>', '', html, flags=re.IGNORECASE)

    # Keep only form-relevant tags
    # Extract: form, input, select, textarea, label, button, option
    relevant_parts = []

    # Find forms
    forms = re.findall(r'<form[^>]*>.*?</form>', html, flags=re.DOTALL | re.IGNORECASE)
    if forms:
        for form in forms:
            relevant_parts.append(clean_form_content(form))
    else:
        # No form tags - look for inputs directly
        inputs = re.findall(r'<(input|select|textarea|button)[^>]*/?>', html, flags=re.IGNORECASE)
        labels = re.findall(r'<label[^>]*>.*?</label>', html, flags=re.DOTALL | re.IGNORECASE)
        relevant_parts.extend(inputs)
        relevant_parts.extend(labels)

    result = '\n'.join(relevant_parts)

    # Truncate if too long
    if len(result) > max_length:
        result = result[:max_length] + '\n... [truncated]'

    return result


def clean_form_content(form_html: str) -> str:
    """Extract just the relevant parts from a form."""
    lines = []

    # Extract inputs with their attributes
    for match in re.finditer(r'<input([^>]*)/?>', form_html, re.IGNORECASE):
        attrs = match.group(1)
        # Keep: type, name, id, placeholder, aria-label, required, value
        cleaned = extract_relevant_attrs(attrs, 'input')
        if cleaned:
            lines.append(f'<input {cleaned}/>')

    # Extract selects
    for match in re.finditer(r'<select([^>]*)>(.*?)</select>', form_html, re.DOTALL | re.IGNORECASE):
        attrs = match.group(1)
        options_html = match.group(2)
        cleaned_attrs = extract_relevant_attrs(attrs, 'select')

        # Extract first few options
        options = re.findall(r'<option[^>]*>([^<]*)</option>', options_html, re.IGNORECASE)[:5]
        options_str = ', '.join(options) if options else ''

        lines.append(f'<select {cleaned_attrs}> options: [{options_str}] </select>')

    # Extract textareas
    for match in re.finditer(r'<textarea([^>]*)>', form_html, re.IGNORECASE):
        attrs = match.group(1)
        cleaned = extract_relevant_attrs(attrs, 'textarea')
        lines.append(f'<textarea {cleaned}></textarea>')

    # Extract labels
    for match in re.finditer(r'<label([^>]*)>([^<]*)</label>', form_html, re.IGNORECASE):
        attrs = match.group(1)
        text = match.group(2).strip()
        if text:
            for_attr = re.search(r'for=["\']([^"\']+)["\']', attrs)
            for_str = f' for="{for_attr.group(1)}"' if for_attr else ''
            lines.append(f'<label{for_str}>{text}</label>')

    # Extract buttons
    for match in re.finditer(r'<button([^>]*)>([^<]*)</button>', form_html, re.IGNORECASE):
        text = match.group(2).strip()
        if text:
            lines.append(f'<button>{text}</button>')

    return '\n'.join(lines)


def extract_relevant_attrs(attrs: str, tag_type: str) -> str:
    """Extract only the attributes we care about."""
    relevant = []

    patterns = [
        (r'type=["\']([^"\']+)["\']', 'type'),
        (r'name=["\']([^"\']+)["\']', 'name'),
        (r'id=["\']([^"\']+)["\']', 'id'),
        (r'placeholder=["\']([^"\']+)["\']', 'placeholder'),
        (r'aria-label=["\']([^"\']+)["\']', 'aria-label'),
        (r'required', 'required'),
        (r'disabled', 'disabled'),
    ]

    for pattern, attr_name in patterns:
        match = re.search(pattern, attrs, re.IGNORECASE)
        if match:
            if attr_name in ['required', 'disabled']:
                relevant.append(attr_name)
            else:
                relevant.append(f'{attr_name}="{match.group(1)}"')

    return ' '.join(relevant)


# Fields that are ambiguous when inside work/education sections
_CONTEXT_SENSITIVE_FIELDS = {'city', 'state', 'zip', 'address'}

# Patterns that indicate work/education context (NOT contact info)
_WORK_EDU_CONTEXT = re.compile(
    r'(job|work|employ|position|company|occupation|school|college|university|'
    r'education|degree|major|gpa|start.?date|end.?date|graduation|employer|'
    r'title.?at|experience)',
    re.IGNORECASE
)


def match_field_heuristically(field_info: dict) -> Optional[str]:
    """
    Try to match a form field to user profile field using heuristics.
    Returns the profile field name if matched, None otherwise.

    Context-aware: won't match city/state/zip/address when the field
    is inside a work history or education section.
    """
    # Combine all identifying info
    identifiers = ' '.join([
        str(field_info.get('name', '')),
        str(field_info.get('id', '')),
        str(field_info.get('placeholder', '')),
        str(field_info.get('aria-label', '')),
        str(field_info.get('label', '')),
    ]).lower()

    for profile_field, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, identifiers, re.IGNORECASE):
                # For context-sensitive fields, check if we're in a work/education section
                if profile_field in _CONTEXT_SENSITIVE_FIELDS:
                    if _WORK_EDU_CONTEXT.search(identifiers):
                        return None  # Skip - this is a work/edu field, not contact info
                return profile_field

    return None


def extract_form_fields(html: str) -> list[dict]:
    """
    Extract all form fields with their identifying information.
    Includes associated label text via <label for="id"> matching.
    """
    fields = []

    # Build label map: field_id -> label text
    label_map = {}
    for match in re.finditer(r'<label[^>]*for=["\']([^"\']+)["\'][^>]*>(.*?)</label>', html, re.DOTALL | re.IGNORECASE):
        field_id = match.group(1)
        label_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        if label_text:
            label_map[field_id] = label_text

    # Find inputs
    for match in re.finditer(r'<input([^>]*)/?>', html, re.IGNORECASE):
        attrs = match.group(1)
        field_id = extract_attr(attrs, 'id')
        field = {
            'tag': 'input',
            'type': extract_attr(attrs, 'type') or 'text',
            'name': extract_attr(attrs, 'name'),
            'id': field_id,
            'placeholder': extract_attr(attrs, 'placeholder'),
            'aria-label': extract_attr(attrs, 'aria-label'),
            'label': label_map.get(field_id, '') if field_id else '',
            'required': 'required' in attrs.lower(),
        }
        fields.append(field)

    # Find selects
    for match in re.finditer(r'<select([^>]*)>', html, re.IGNORECASE):
        attrs = match.group(1)
        field_id = extract_attr(attrs, 'id')
        field = {
            'tag': 'select',
            'type': 'select',
            'name': extract_attr(attrs, 'name'),
            'id': field_id,
            'aria-label': extract_attr(attrs, 'aria-label'),
            'label': label_map.get(field_id, '') if field_id else '',
            'required': 'required' in attrs.lower(),
        }
        fields.append(field)

    # Find textareas
    for match in re.finditer(r'<textarea([^>]*)>', html, re.IGNORECASE):
        attrs = match.group(1)
        field_id = extract_attr(attrs, 'id')
        field = {
            'tag': 'textarea',
            'type': 'textarea',
            'name': extract_attr(attrs, 'name'),
            'id': field_id,
            'placeholder': extract_attr(attrs, 'placeholder'),
            'aria-label': extract_attr(attrs, 'aria-label'),
            'label': label_map.get(field_id, '') if field_id else '',
            'required': 'required' in attrs.lower(),
        }
        fields.append(field)

    return fields


def extract_attr(attrs: str, attr_name: str) -> Optional[str]:
    """Extract a single attribute value."""
    match = re.search(rf'{attr_name}=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
    return match.group(1) if match else None


def generate_field_mapping(
    form_html: str,
    user_profile: dict,
    use_llm_callback=None
) -> dict:
    """
    Generate a mapping of CSS selectors to values.

    1. First tries heuristic matching (free)
    2. Falls back to LLM for unmatched fields

    Returns: { "#first_name": "John", "[name='email']": "john@example.com", ... }
    """
    fields = extract_form_fields(form_html)
    mapping = {}
    unmatched = []

    for field in fields:
        # Skip hidden, submit, button types
        if field.get('type') in ['hidden', 'submit', 'button', 'reset']:
            continue

        # Try heuristic match first
        profile_key = match_field_heuristically(field)

        if profile_key and profile_key in user_profile:
            # Build selector
            selector = build_selector(field)
            if selector:
                mapping[selector] = user_profile[profile_key]
        else:
            unmatched.append(field)

    # If there are unmatched fields and we have an LLM callback, use it
    if unmatched and use_llm_callback:
        llm_mapping = use_llm_callback(unmatched, user_profile)
        mapping.update(llm_mapping)

    return mapping


def build_selector(field: dict) -> Optional[str]:
    """Build a CSS selector for a field."""
    if field.get('id'):
        return f"#{field['id']}"
    if field.get('name'):
        return f"[name=\"{field['name']}\"]"
    if field.get('aria-label'):
        return f"[aria-label=\"{field['aria-label']}\"]"
    return None
