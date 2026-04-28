import asyncio
import os
import re
from abc import ABC, abstractmethod
from typing import Any


class BaseToMarkdownConverter(ABC):
    file_extension_length = 0

    def __init__(
            self,
            docs_dir: str,
            md_dir: str,
    ):
        self._docs_dir = docs_dir
        self._md_dir = md_dir

    async def convert_docs_in_dir_to_markdown(self) -> None:
        doc_name_list = self._get_doc_name_list()
        tasks = [self._async_convert_document_to_markdown(doc_name) for doc_name in doc_name_list]
        await asyncio.gather(*tasks)

    async def _async_convert_document_to_markdown(self, doc_name: str) -> None:
        await asyncio.to_thread(
            self._sync_convert_document_to_markdown,
            doc_name=doc_name,
        )

    @abstractmethod
    def _sync_convert_document_to_markdown(self, doc_name: str) -> None:
        pass

    def _write_in_md_file(self, md_lines: list[str], doc_name: str) -> None:
        with open(f'{self._md_dir}/{doc_name}.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

    @staticmethod
    def _convert_numbers(text: str) -> str:
        text = re.sub(r'^(\d+)\.', r'\1\\.', text)
        text = re.sub(r'^(\d+)\)', r'- ', text)
        return text

    def _get_doc_name_list(self) -> list[str]:
        file_list = os.listdir(self._docs_dir)
        return [file[:-self.file_extension_length] for file in file_list]

    @staticmethod
    @abstractmethod
    def _is_header(string: Any) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def _is_specific_header(string: Any) -> bool:
        pass
