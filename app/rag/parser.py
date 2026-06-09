import fitz

from app.observability.decorators import (
    observe
)


class PDFParser:

    @staticmethod
    @observe("PDF Parsing - Step 2.1")
    async def extract_pages(
        file_path: str,
        user_id: str,
        document_id: str,
        filename: str
    ):

        pdf = fitz.open(file_path)

        pages = []

        for idx, page in enumerate(
            pdf,
            start=1
        ):

            pages.append(
                {
                    "user_id": user_id,
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": idx,
                    "text": page.get_text()
                }
            )

        pdf.close()

        return pages