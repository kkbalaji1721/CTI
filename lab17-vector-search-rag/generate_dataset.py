"""Generate a reproducible 5,000-document threat dataset and 384-D feature vectors."""

import json
import random
from pathlib import Path

import numpy as np

from embeddings import LOCAL_DIMENSIONS, local_embeddings


OUT = Path("results")
COUNT = 5000
SEED = 17017


def generate() -> tuple[list[dict], np.ndarray]:
    rng = random.Random(SEED)
    topics = [
        ("ransomware", "encrypts endpoints, steals data, and abuses exposed remote access"),
        ("phishing", "uses deceptive email links, credential theft, and malicious attachments"),
        ("cloud identity", "abuses refresh tokens, OAuth permissions, and mailbox rules"),
        ("web shell", "exploits vulnerable servers and creates persistent remote command access"),
        ("supply chain", "compromises signed packages, build pipelines, and vendor updates"),
        ("botnet", "uses command servers, vulnerable devices, and distributed traffic"),
        ("data exfiltration", "stages sensitive files and transfers them to external infrastructure"),
        ("privilege escalation", "misuses service accounts and weak access controls"),
        ("DNS tunneling", "encodes command traffic in unusual domain lookups"),
        ("endpoint defense evasion", "disables monitoring agents and modifies security settings"),
    ]
    sources = ["CISA", "CERT", "MITRE ATT&CK", "NIST", "Vendor Advisory"]
    documents = []
    texts = []
    for index in range(COUNT):
        topic, behavior = topics[index % len(topics)]
        source = sources[index % len(sources)]
        variant = rng.randrange(1, 1000000)
        text = (
            f"Threat report {index:05d} from {source}: {topic} activity, incident {variant}. "
            f"Observed behavior {behavior}. Defenders should review authentication logs, "
            f"network telemetry, endpoint alerts, and software inventory for {topic} indicators. "
            f"Contain affected assets, preserve forensic evidence, rotate exposed credentials, "
            f"and apply verified security updates. Detection context: {topic} {behavior}."
        )
        documents.append({"id": index, "source": source, "topic": topic, "text": text})
        texts.append(text)
    vectors = np.asarray(local_embeddings(texts, LOCAL_DIMENSIONS), dtype=np.float32)
    OUT.mkdir(exist_ok=True)
    with (OUT / "benchmark_dataset.jsonl").open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(json.dumps(document, ensure_ascii=False) + "\n")
    np.save(OUT / "benchmark_vectors.npy", vectors)
    print(f"Generated {len(documents)} documents; vectors shape={vectors.shape}.")
    return documents, vectors


if __name__ == "__main__":
    generate()
