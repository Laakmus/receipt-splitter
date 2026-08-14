import pdfplumber
import pytesseract


def rasterize_pdf(pdf_path):
    """Convert every page of a PDF into an image.

    Returns one image per page. Uses 300 DPI, which is high enough for the
    small print on a receipt.
    """
    with pdfplumber.open(pdf_path) as pdf:
        return [page.to_image(resolution=300).original for page in pdf.pages]


def run_ocr(image):
    """Read text from an image using Polish OCR.

    Uses --psm 6, which tells tesseract to treat the page as one uniform
    block of text. The default mode detects columns, separates product
    names from prices and drops the numbers.
    """
    return pytesseract.image_to_string(image, lang='pol', config="--psm 6")


def extract_receipt_text(pdf_path):
    """Read the whole receipt from a PDF file.

    Rasterizes every page, runs OCR on each of them and joins the results
    into a single text. Page footers stay in the output, so the parser has
    to skip them.
    """
    pages = rasterize_pdf(pdf_path)
    text = ""
    for page in pages:
        text += run_ocr(page) + "\n"
    return text
