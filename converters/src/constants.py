import pathlib

BASE_DIR = pathlib.Path(__file__).parent.parent

DOCS_DIR = pathlib.Path(BASE_DIR, "documents")
DOCX_DOCS_DIR = pathlib.Path(DOCS_DIR, "docx")
PDF_DOCS_DIR = pathlib.Path(DOCS_DIR, "pdf")
RTF_DOCS_DIR = pathlib.Path(DOCS_DIR, "rtf")

MD_DIR = pathlib.Path(BASE_DIR, "markdowns")
DOCX_MD_DIR = pathlib.Path(MD_DIR, "docx")
PDF_MD_DIR = pathlib.Path(MD_DIR, "pdf")
RTF_MD_DIR = pathlib.Path(MD_DIR, "rtf")
