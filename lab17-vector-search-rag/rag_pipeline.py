"""Threat-intelligence RAG pipeline with Atlas and clearly labeled local modes."""

import json
import os
import re
import urllib.error
import urllib.request
from uuid import uuid4

from conversation_memory import ConversationMemory
from embeddings import EmbeddingProvider, cosine_similarity
from threat_intel import DOCUMENTS


def chunk_text(text: str, window_words: int = 100, overlap_words: int = 20) -> list[str]:
    if window_words <= 0 or overlap_words < 0 or overlap_words >= window_words:
        raise ValueError("Require window_words > overlap_words >= 0.")
    words = text.split()
    step = window_words - overlap_words
    return [" ".join(words[start : start + window_words]) for start in range(0, len(words), step)]


class RAGPipeline:
    def __init__(self, database=None, conversation_id: str | None = None) -> None:
        self.database = database
        self.embeddings = EmbeddingProvider()
        self.conversation_id = conversation_id or uuid4().hex
        self.memory = ConversationMemory(database, self.conversation_id)
        self._chunks: list[dict] = []
        self._seed()

    def _seed(self) -> None:
        for document in DOCUMENTS:
            for index, text in enumerate(chunk_text(document["text"])):
                self._chunks.append(
                    {
                        "text": text,
                        "source": document["source"],
                        "chunk_index": index,
                        "embedding": self.embeddings.embed([text])[0],
                    }
                )
        if self.database:
            self.database.ingest_chunks(self._chunks, self.embeddings.dimensions)

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        query_vector = self.embeddings.embed([query], input_type="query")[0]
        if self.database:
            return self.database.vector_search(query_vector, top_k)
        scored = [
            {**chunk, "score": cosine_similarity(query_vector, chunk["embedding"])}
            for chunk in self._chunks
        ]
        return sorted(scored, key=lambda row: row["score"], reverse=True)[:top_k]

    @staticmethod
    def _generate(prompt_messages: list[dict[str, str]]) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            latest = next(
                (message["content"] for message in reversed(prompt_messages) if message["role"] == "user"),
                "",
            )
            current_query = latest.rsplit("\n\nQuestion:", 1)[-1].strip()
            previous_questions = [
                message["content"]
                for message in prompt_messages[:-1]
                if message["role"] == "user"
            ]
            if not previous_questions:
                return (
                    "Local memory demo (not LLM-generated): this is the first question in this "
                    "conversation. Ask 'What did I ask you previously?' after another question "
                    "to verify session memory."
                )

            previous_question = previous_questions[-1]
            recall_requested = any(
                phrase in current_query.lower()
                for phrase in (
                    "what did i ask",
                    "what was my previous question",
                    "previous question",
                    "last question",
                    "question before",
                    "what did i say",
                )
            )
            if recall_requested:
                return (
                    "Local conversation-memory response (not LLM-generated): your previous "
                    f"question was: {previous_question}"
                )
            return (
                "Local conversation-memory response (not LLM-generated): I remember your "
                f"previous question was: {previous_question}. The retrieved threat context is "
                "available for this turn, but this offline fallback does not generate an LLM answer."
            )
        payload = json.dumps(
            {"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "messages": prompt_messages, "temperature": 0.2}
        ).encode()
        request = urllib.request.Request(
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode())["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as exc:
            raise RuntimeError(f"LLM generation failed: {exc}") from exc

    def chat(self, query: str, top_k: int = 3) -> tuple[str, list[dict]]:
        results = self.retrieve(query, top_k)
        history = self.memory.last_messages(5)
        context = "\n\n".join(f"[{row['source']}] {row['text']}" for row in results)
        messages = [
            {"role": "system", "content": "Answer using the supplied threat-intelligence context. State when evidence is insufficient."},
            *history,
            {"role": "user", "content": f"Retrieved context:\n{context}\n\nQuestion: {query}"},
        ]
        answer = self._generate(messages)
        self.memory.add("user", query)
        self.memory.add("assistant", answer)
        return answer, results
