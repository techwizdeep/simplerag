# backend/app/services/chathistory.py
from typing import Dict, List
from threading import Lock
from app.models.chat import Message

class ChatHistoryStore:
    """
    Very simple in-memory chat history store.

    - Stores history per user_id (string).
    - NOT persistent: data is lost when the app restarts.
    - Thread-safe via a global lock (good enough for demo / low traffic).
    """

    def __init__(self) -> None:
        self._lock = Lock()
        # user_id -> List[Message]
        self._store: Dict[str, List[Message]] = {}

    def get_history(self, user_id: str) -> List[Message]:
        """
        Return the full chat history for a user.
        If there is no history, returns an empty list.
        """
        with self._lock:
            return list(self._store.get(user_id, []))

    def append(self, user_id: str, message: Message) -> None:
        """
        Append a single Message to a user's history.
        """
        with self._lock:
            if user_id not in self._store:
                self._store[user_id] = []
            self._store[user_id].append(message)

    def set_history(self, user_id: str, messages: List[Message]) -> None:
        """
        Replace the entire history for a user with the given list.
        """
        with self._lock:
            self._store[user_id] = list(messages)

    def clear(self, user_id: str) -> None:
        """
        Clear history for a single user.
        """
        with self._lock:
            self._store.pop(user_id, None)

    def clear_all(self) -> None:
        """
        Clear history for ALL users. Use carefully.
        """
        with self._lock:
            self._store.clear()


# Create a single global instance to be imported and reused
chat_history_store = ChatHistoryStore()
