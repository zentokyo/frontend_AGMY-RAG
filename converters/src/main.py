import asyncio

from src.constants import RTF_DOCS_DIR, RTF_MD_DIR
from src.converters.rtf import RTFToMarkdownConverter


async def main() -> None:
    rtf_converter = RTFToMarkdownConverter(
        docs_dir=RTF_DOCS_DIR,
        md_dir = RTF_MD_DIR,
    )
    await rtf_converter.convert_docs_in_dir_to_markdown()

if __name__ == "__main__":
    asyncio.run(main())
