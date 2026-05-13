import re

_PATTERNS = [
    (r'AKIA[0-9A-Z]{16}', '<AWS_ACCESS_KEY>'),
    (r'(?i)(aws_secret_access_key\s*=\s*)\S+', r'\1<REDACTED>'),
    (r'ghp_[A-Za-z0-9]{36}', '<GITHUB_TOKEN>'),
    (r'ghs_[A-Za-z0-9]{36}', '<GITHUB_TOKEN>'),
    (r'github_pat_[A-Za-z0-9_]{82}', '<GITHUB_TOKEN>'),
    (r'https?://[^:@\s]+:[^@\s]+@[^\s]+', '<URL_WITH_CREDENTIALS>'),
    (r'(?i)(api[_-]?key\s*[:=]\s*)[\'"]?\S+[\'"]?', r'\1<REDACTED>'),
    (r'(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*', r'\1<REDACTED>'),
    (r'(?i)(token\s*[:=]\s*)[\'"]?\S+[\'"]?', r'\1<REDACTED>'),
    (r'sk-ant-[A-Za-z0-9\-_]{40,}', '<ANTHROPIC_KEY>'),
]


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text
