from types import SimpleNamespace
import unittest

from qdrant_client import models

from src.cli.reindex_admin_documents import (
    _delete_previous_staging_collection,
    _publish_staging_collection,
)


class FakeQdrantClient:
    def __init__(self, aliases=None, collections=None):
        self.aliases = list(aliases or [])
        self.collections = set(collections or [])
        self.deleted_collections: list[str] = []
        self.alias_operation_batches: list[list[models.ChangeAliasesOperation]] = []

    def get_aliases(self):
        return SimpleNamespace(aliases=self.aliases)

    def get_collection(self, collection_name: str):
        if collection_name not in self.collections:
            raise RuntimeError(f"missing collection: {collection_name}")
        return SimpleNamespace()

    def delete_collection(self, collection_name: str):
        self.deleted_collections.append(collection_name)
        self.collections.discard(collection_name)

    def update_collection_aliases(self, change_aliases_operations):
        self.alias_operation_batches.append(change_aliases_operations)
        for operation in change_aliases_operations:
            if isinstance(operation, models.DeleteAliasOperation):
                alias_name = operation.delete_alias.alias_name
                self.aliases = [alias for alias in self.aliases if alias.alias_name != alias_name]
            elif isinstance(operation, models.CreateAliasOperation):
                alias = operation.create_alias
                self.aliases.append(
                    SimpleNamespace(
                        alias_name=alias.alias_name,
                        collection_name=alias.collection_name,
                    )
                )


class FakeQdrantStore:
    def __init__(self, client: FakeQdrantClient):
        self.client = client


class ReindexAdminDocumentsTests(unittest.TestCase):
    def test_publish_switches_existing_alias_atomically(self):
        client = FakeQdrantClient(
            aliases=[
                SimpleNamespace(
                    alias_name="assistant_knowledge",
                    collection_name="assistant_knowledge__staging__old",
                )
            ],
            collections={
                "assistant_knowledge__staging__old",
                "assistant_knowledge__staging__new",
            },
        )

        previous_collection = _publish_staging_collection(
            FakeQdrantStore(client),
            "assistant_knowledge",
            "assistant_knowledge__staging__new",
        )

        self.assertEqual(previous_collection, "assistant_knowledge__staging__old")
        self.assertEqual(len(client.alias_operation_batches), 1)
        self.assertIsInstance(client.alias_operation_batches[0][0], models.DeleteAliasOperation)
        self.assertIsInstance(client.alias_operation_batches[0][1], models.CreateAliasOperation)
        self.assertEqual(client.aliases[0].collection_name, "assistant_knowledge__staging__new")

    def test_publish_bootstraps_alias_when_live_name_is_collection(self):
        client = FakeQdrantClient(
            collections={
                "assistant_knowledge",
                "assistant_knowledge__staging__new",
            },
        )

        previous_collection = _publish_staging_collection(
            FakeQdrantStore(client),
            "assistant_knowledge",
            "assistant_knowledge__staging__new",
        )

        self.assertIsNone(previous_collection)
        self.assertEqual(client.deleted_collections, ["assistant_knowledge"])
        self.assertNotIn("assistant_knowledge", client.collections)
        self.assertEqual(client.aliases[0].alias_name, "assistant_knowledge")
        self.assertEqual(client.aliases[0].collection_name, "assistant_knowledge__staging__new")

    def test_cleanup_deletes_only_managed_previous_staging_collection(self):
        client = FakeQdrantClient(
            collections={
                "assistant_knowledge__staging__old",
                "manually_created_collection",
            },
        )
        store = FakeQdrantStore(client)

        _delete_previous_staging_collection(
            store,
            "assistant_knowledge__staging__old",
            live_collection="assistant_knowledge",
            current_staging_collection="assistant_knowledge__staging__new",
        )
        _delete_previous_staging_collection(
            store,
            "manually_created_collection",
            live_collection="assistant_knowledge",
            current_staging_collection="assistant_knowledge__staging__new",
        )

        self.assertEqual(client.deleted_collections, ["assistant_knowledge__staging__old"])
        self.assertIn("manually_created_collection", client.collections)


if __name__ == "__main__":
    unittest.main()
