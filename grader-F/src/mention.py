import re
from enum import Enum


class MentionType(Enum):
    USER = "USER"
    CHANNEL = "CHANNEL"
    ALL = "ALL"


class MentionParser:
    def parse(self, content):
        """Extract @username mentions, excluding @all and @here. Deduplicated."""
        matches = re.findall(r'@(\w+)', content)
        seen = set()
        result = []
        for m in matches:
            if m.lower() in ('all', 'here'):
                continue
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result

    def parse_channel_mentions(self, content):
        """Extract #channel mentions."""
        matches = re.findall(r'#(\w+)', content)
        seen = set()
        result = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result

    def parse_all_mentions(self, content):
        """Return [MentionType.ALL] if @all or @here is present."""
        if re.search(r'@(all|here)\b', content, re.IGNORECASE):
            return [MentionType.ALL]
        return []

    def parse_all_types(self, content):
        """Parse all mention types, returning list of (MentionType, name) tuples."""
        result = []
        for match in re.finditer(r'[@#](\w+)', content):
            full = match.group(0)
            name = match.group(1)
            if full.startswith('@'):
                if name.lower() in ('all', 'here'):
                    result.append((MentionType.ALL, name))
                else:
                    result.append((MentionType.USER, name))
            elif full.startswith('#'):
                result.append((MentionType.CHANNEL, name))
        return result
