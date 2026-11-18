"""Focused tests for the lab's offline-safe behaviors."""

import unittest
import os
from unittest.mock import patch

from conversation_memory import ConversationMemory
from embeddings import EmbeddingProvider
from exact_search import exact_top_k, recall_percent
from rag_pipeline import RAGPipeline, chunk_text


class Lab17Tests(unittest.TestCase):
    def test_sliding_window_uses_requested_overlap(self):
        words = [f"word{i}" for i in range(220)]
        chunks = chunk_text(" ".join(words), window_words=100, overlap_words=20)
        self.assertEqual(len(chunks[0].split()), 100)
        self.assertEqual(chunks[0].split()[-20:], chunks[1].split()[:20])
        self.assertEqual(chunks[1].split()[-20:], chunks[2].split()[:20])

    def test_local_embedding_has_configured_dimension_and_is_deterministic(self):
        provider = EmbeddingProvider()
        if provider.provider.startswith("local"):
            first = provider.embed(["ransomware phishing"])[0]
            self.assertEqual(len(first), 384)
            self.assertEqual(first, provider.embed(["ransomware phishing"])[0])

    def test_rag_retrieves_three_chunks_and_keeps_five_messages(self):
        pipeline = RAGPipeline()
        answer, sources = pipeline.chat("How should defenders respond to ransomware?")
        self.assertIn("Local memory demo (not LLM-generated)", answer)
        self.assertEqual(len(sources), 3)
        self.assertEqual(len(pipeline.memory.last_messages()), 2)

        memory = ConversationMemory()
        for index in range(6):
            memory.add("user", f"question {index}")
        self.assertEqual([row["content"] for row in memory.last_messages(5)], [
            f"question {index}" for index in range(1, 6)
        ])

    def test_follow_up_prompt_contains_recent_conversation(self):
        pipeline = RAGPipeline()
        captured_prompts = []

        def capture(messages):
            captured_prompts.append(messages)
            return "captured response"

        with patch.object(RAGPipeline, "_generate", side_effect=capture):
            pipeline.chat("First question about ransomware")
            pipeline.chat("What should I inspect next?")

        follow_up = captured_prompts[1]
        self.assertTrue(any("First question about ransomware" in item["content"] for item in follow_up))
        self.assertTrue(any(item["role"] == "assistant" and item["content"] == "captured response" for item in follow_up))
        self.assertTrue(any("What should I inspect next?" in item["content"] for item in follow_up))

    def test_offline_demo_recalls_and_stores_previous_question(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "VOYAGE_API_KEY": ""}):
            pipeline = RAGPipeline()
            first_question = "Which logs should I check for ransomware?"
            first_answer, _ = pipeline.chat(first_question)
            recalled_answer, _ = pipeline.chat("What did I ask you previously?")

        self.assertIn("not LLM-generated", first_answer)
        self.assertIn("not LLM-generated", recalled_answer)
        self.assertIn(first_question, recalled_answer)
        self.assertEqual(
            pipeline.memory.last_messages(5),
            [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first_answer},
                {"role": "user", "content": "What did I ask you previously?"},
                {"role": "assistant", "content": recalled_answer},
            ],
        )

    def test_local_memory_is_isolated_per_session(self):
        first_session = ConversationMemory()
        second_session = ConversationMemory()
        first_session.add("user", "session-one question")

        self.assertNotEqual(first_session.conversation_id, second_session.conversation_id)
        self.assertEqual(first_session.last_messages(5)[0]["content"], "session-one question")
        self.assertEqual(second_session.last_messages(5), [])

    def test_exact_top_k_is_its_own_ground_truth(self):
        import numpy as np

        vectors = np.asarray([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
        query = np.asarray([1.0, 0.0])
        exact = exact_top_k(vectors, query, k=2)

        self.assertEqual(recall_percent(exact, exact), 100.0)
        self.assertEqual(len(exact), 2)


if __name__ == "__main__":
    unittest.main()
