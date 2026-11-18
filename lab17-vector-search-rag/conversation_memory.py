"""Conversation persistence for Atlas and the explicitly local demo mode."""

from uuid import uuid4


class ConversationMemory:
    def __init__(self, database=None, conversation_id: str | None = None) -> None:
        self.database = database
        self.conversation_id = conversation_id or uuid4().hex
        self._messages: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        if self.database:
            self.database.add_message(self.conversation_id, role, content)
        else:
            self._messages.append({"role": role, "content": content})

    def last_messages(self, limit: int = 5) -> list[dict[str, str]]:
        if self.database:
            return self.database.recent_messages(self.conversation_id, limit)
        return self._messages[-limit:]
