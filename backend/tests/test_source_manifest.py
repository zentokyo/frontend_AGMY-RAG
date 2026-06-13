import json
import tempfile
import unicodedata
import unittest
from pathlib import Path

from src.cli.sync_source_manifest import load_source_entries


class SourceManifestTests(unittest.TestCase):
    def test_load_source_entries_resolves_theme_files_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            theme_files_dir = root / "theme_files"
            theme_files_dir.mkdir()
            source_path = theme_files_dir / "source.pdf"
            source_path.write_bytes(b"pdf")

            manifest_path = root / "source_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "theme_order": 1,
                                "theme_title": "Theme",
                                "path": "${THEME_FILES}/source.pdf",
                                "filename": "source.pdf",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            entries = load_source_entries(
                manifest_path,
                theme_files_dir=theme_files_dir,
            )

        self.assertEqual(entries[0].source_path, source_path)

    def test_load_source_entries_resolves_unicode_normalized_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            downloads_dir = root / "downloads"
            kaf_epid_dir = root / "kaf"
            downloads_dir.mkdir()
            kaf_epid_dir.mkdir()

            actual_name = unicodedata.normalize("NFD", "Приложения.docx")
            actual_path = kaf_epid_dir / actual_name
            actual_path.write_bytes(b"docx")

            manifest_path = root / "source_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "theme_order": 4,
                                "theme_title": "Theme",
                                "path": "${KAF_EPID}/Приложения.docx",
                                "filename": "prilozheniia.docx",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            entries = load_source_entries(
                manifest_path,
                downloads_dir=downloads_dir,
                kaf_epid_dir=kaf_epid_dir,
            )

        self.assertEqual(entries[0].source_path, actual_path)
        self.assertEqual(entries[0].content_type, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_load_source_entries_rejects_duplicate_block_filename_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            downloads_dir = root / "downloads"
            kaf_epid_dir = root / "kaf"
            downloads_dir.mkdir()
            kaf_epid_dir.mkdir()

            manifest_path = root / "source_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "theme_order": 1,
                                "theme_title": "Theme",
                                "path": "${DOWNLOADS}/first.pdf",
                                "filename": "source.pdf",
                            },
                            {
                                "theme_order": 1,
                                "theme_title": "Theme",
                                "path": "${DOWNLOADS}/second.pdf",
                                "filename": "source.pdf",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate block/filename"):
                load_source_entries(
                    manifest_path,
                    downloads_dir=downloads_dir,
                    kaf_epid_dir=kaf_epid_dir,
                )


if __name__ == "__main__":
    unittest.main()
