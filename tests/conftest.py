from pathlib import Path

import pytest


@pytest.fixture
def raw_ocr_text():
    path = Path(__file__).parent / "fixtures" / "ocr_samples" / "receipt_1_raw_ocr.txt"
    return path.read_text()