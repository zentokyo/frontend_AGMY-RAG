import re

from striprtf.striprtf import rtf_to_text

from src.converters.base import BaseToMarkdownConverter


class RTFToMarkdownConverter(BaseToMarkdownConverter):
    file_extension_length = 4  # Учитываем точку *.rtf

    def _sync_convert_document_to_markdown(self, doc_name: str) -> None:
        text = self._get_text_from_rtf(doc_name)
        lines = text.split("\n")

        md_lines = []
        previous_header_idx = 0
        previous_header_is_specific = False
        line_idx = 0

        for line in lines:
            text = line

            if not text:
                continue

            if self._is_header(text):
                idx_diff = abs(line_idx - previous_header_idx)
                if idx_diff == 2:
                    if (self._is_specific_header(text) and previous_header_is_specific) or (
                            not self._is_specific_header(text) and not previous_header_is_specific):
                        md_lines[previous_header_idx] = f"{md_lines[previous_header_idx]} {text}"
                        continue
                if self._is_specific_header(text):
                    text = f"# {text}"
                    previous_header_is_specific = True
                else:
                    text = f"## {text}"
                    previous_header_is_specific = False
                previous_header_idx = line_idx

            text = self._convert_numbers(text)

            md_lines.append(text)
            md_lines.append("")
            line_idx += 2  # Увеличиваем на 2 из-за пустой строки

        self._write_in_md_file(md_lines, doc_name)

    def _get_text_from_rtf(self, doc_name: str) -> str:
        with open(f"{self._docs_dir}/{doc_name}.rtf", 'r', encoding="cp1251", errors='ignore') as file:
            rtf_content = file.read()

        return rtf_to_text(rtf_content)

    @staticmethod
    def _is_specific_header(string: str) -> bool:
        return False

    @staticmethod
    def _is_header(string: str) -> bool:
        if (
                (string.isupper() and not re.match(r"\b[А-ЯЁ]\.[А-ЯЁ]\.[А-ЯЁ][А-ЯЁ]+\b", string))
                or re.match(r"^(Глава|Раздел|Часть)", string, re.IGNORECASE)
        ):
            return True
        return False
