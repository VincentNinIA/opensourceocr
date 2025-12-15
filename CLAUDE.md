# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit web application that performs OCR (Optical Character Recognition) on PDF documents and images using Mistral AI's vision models. The app provides two OCR engines with different capabilities for handling document text extraction.

## Running the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Dependencies Installation

```bash
pip install -r requirements.txt
```

## Configuration

The application requires a Mistral API key stored in a `.env` file:
```
MISTRAL_API_KEY=your_key_here
```

Use `.env.example` as a template.

## Architecture

### Two OCR Engines

The app supports two different OCR approaches via `ocr_with_mistral()`:

1. **OCR dédié** (`use_pixtral=False`):
   - Uses Mistral's dedicated OCR endpoint: `client.ocr.process()`
   - Model: `mistral-ocr-latest`
   - Returns structured Markdown with proper table formatting
   - Processes all pages automatically via `ocr_response.pages`

2. **Pixtral** (`use_pixtral=True`):
   - Uses the vision chat model: `client.chat.complete()`
   - Model: `pixtral-12b-2409`
   - Accepts custom prompts for better control over output format
   - Current prompt instructs model to describe tables line-by-line instead of Markdown tables
   - Better for handling complex tables or customizing output format

### Document Processing Flow

1. File upload (PDF or image) → `st.file_uploader()`
2. Convert to base64 → `encode_file_to_base64()`
3. Send to Mistral API → `ocr_with_mistral(file_base64, file_type, api_key, use_pixtral)`
4. Display results in two tabs:
   - Markdown rendered view
   - Raw text view
5. Download options: `.md` or `.txt`

### Key Implementation Details

- PDFs are sent directly as base64-encoded `data:application/pdf;base64,...` (no intermediate conversion needed)
- Images use `data:image/jpeg;base64,...` format
- The dedicated OCR endpoint iterates through `ocr_response.pages` to handle multi-page PDFs
- Pixtral mode processes the entire document in one request but may have content length limitations

## Common Issues

### API Errors

- **401 Unauthorized**: Invalid or missing API key in `.env`
- **503 Service Unavailable**: Mistral backend temporarily down, retry after waiting
- **400 Invalid Request**: Format error (e.g., trying to send PDF to image endpoint)

### Streamlit Compatibility

The app uses `use_column_width=True` for image display (older Streamlit syntax). If upgrading Streamlit, consider changing to `use_container_width=True`.
