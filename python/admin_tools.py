"""
ASMU RAG Admin Tools - Qdrant maintenance helper.

Usage:
  python admin_tools.py --action delete --file <path_or_partial_path>
"""

import argparse
import os
import sys

from qdrant_client import QdrantClient, models


def delete_chunks(client: QdrantClient, collection: str, file_identifier: str) -> int:
    """Delete every chunk whose 'source' payload contains file_identifier."""
    ids_to_delete = []
    offset = None

    try:
        while True:
            points, offset = client.scroll(
                collection_name=collection,
                limit=1000,
                offset=offset,
                with_payload=["source"],
                with_vectors=False,
            )
            for point in points:
                source = str((point.payload or {}).get("source", ""))
                if file_identifier in source:
                    ids_to_delete.append(point.id)
            if offset is None:
                break
    except Exception as exc:
        print(f"[admin_tools] Qdrant query failed: {exc}", file=sys.stderr)
        return 0

    if not ids_to_delete:
        print(f"[admin_tools] No chunks found for: {file_identifier}")
        return 0

    client.delete(
        collection_name=collection,
        points_selector=models.PointIdsList(points=ids_to_delete),
        wait=True,
    )
    print(f"[admin_tools] Deleted {len(ids_to_delete)} chunks for: {file_identifier}")
    return len(ids_to_delete)


def main():
    parser = argparse.ArgumentParser(description="ASMU RAG Qdrant admin helper")
    parser.add_argument("--action", required=True, choices=["delete"], help="Action to perform")
    parser.add_argument("--file", required=True, help="File path or partial source payload to match")
    parser.add_argument(
        "--url",
        default=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
        help="Qdrant URL",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("QDRANT_COLLECTION", "assistant_knowledge"),
        help="Qdrant collection name",
    )
    parser.add_argument("--db-path", help="Deprecated legacy option; ignored")
    args = parser.parse_args()

    client = QdrantClient(url=args.url)
    try:
        client.get_collection(args.collection)
    except Exception:
        print(f"[admin_tools] Collection '{args.collection}' not found at {args.url}", file=sys.stderr)
        sys.exit(1)

    if args.action == "delete":
        count = delete_chunks(client, args.collection, args.file)
        sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
