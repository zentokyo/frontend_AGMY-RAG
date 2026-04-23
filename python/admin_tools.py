"""
AGMY RAG Admin Tools — ChromaDB maintenance helper.

Usage:
  python admin_tools.py --action delete --file <path_or_partial_path> --db-path <chroma_dir>

Examples:
  # Delete all chunks originating from a specific PDF:
  python admin_tools.py --action delete \
      --file /path/to/ai_support/knowledge_base/abc123.pdf \
      --db-path /path/to/ai_support/db_metadata_v5
"""

import argparse
import sys

import chromadb


def delete_chunks(collection, file_identifier: str) -> int:
    """Delete every chunk whose 'source' metadata contains file_identifier."""
    # ChromaDB's $contains operator on string fields
    try:
        results = collection.get(
            where={"source": {"$contains": file_identifier}},
            include=[],  # IDs only — no need to fetch embeddings/documents
        )
    except Exception as exc:
        print(f"[admin_tools] Query failed: {exc}", file=sys.stderr)
        return 0

    ids = results.get("ids", [])
    if not ids:
        print(f"[admin_tools] No chunks found for: {file_identifier}")
        return 0

    collection.delete(ids=ids)
    print(f"[admin_tools] Deleted {len(ids)} chunks for: {file_identifier}")
    return len(ids)


def main():
    parser = argparse.ArgumentParser(description="AGMY RAG ChromaDB admin helper")
    parser.add_argument("--action",  required=True, choices=["delete"],
                        help="Action to perform (currently: delete)")
    parser.add_argument("--file",    required=True,
                        help="File path or partial name to match in chunk 'source' metadata")
    parser.add_argument("--db-path", default="./db_metadata_v5",
                        help="Path to the ChromaDB persistent directory")
    parser.add_argument("--collection", default="langchain",
                        help="ChromaDB collection name (default: langchain)")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=args.db_path)

    try:
        collection = client.get_collection(args.collection)
    except Exception:
        print(f"[admin_tools] Collection '{args.collection}' not found in {args.db_path}",
              file=sys.stderr)
        sys.exit(1)

    if args.action == "delete":
        count = delete_chunks(collection, args.file)
        sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
