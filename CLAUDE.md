# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit web application that performs OCR (Optical Character Recognition) on images using Mistral AI's dedicated OCR endpoint. The app supports optional table detection and extraction using PaddleOCR.

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

### OCR Engine

The app uses Mistral AI's dedicated OCR endpoint via `ocr_with_mistral()`:

- Uses `client.ocr.process()` method
- Model: `mistral-ocr-latest`
- Returns structured Markdown with proper table formatting
- Processes all pages automatically via `ocr_response.pages`

### Document Processing Flow

**Standard Mode:**
1. Image upload (PNG/JPG/JPEG) → `st.file_uploader()`
2. Convert to base64 → `encode_file_to_base64()`
3. Send to Mistral API → `ocr_with_mistral(file_base64, api_key)`
4. Display results in two tabs:
   - Markdown rendered view
   - Raw text view
5. Download options: `.md` or `.txt`

**Table Detection Mode (optional):**
1. Image upload → detect tables with PaddleOCR's PPStructureV3
2. Crop each detected table with padding
3. Upscale cropped regions for better quality
4. Process each table separately through Mistral OCR
5. Validate and combine results with quality indicators

### Key Implementation Details

- Images are sent as base64-encoded `data:image/jpeg;base64,...`
- Table detection uses PaddleOCR with optimized settings (English only, no angle classification, CPU mode)
- Results include quality metrics: table type (chemistry/mechanical/generic) and column stability

## Common Issues

### API Errors

- **401 Unauthorized**: Invalid or missing API key in `.env`
- **503 Service Unavailable**: Mistral backend temporarily down, retry after waiting
- **400 Invalid Request**: Format error (e.g., trying to send PDF to image endpoint)

### Table Detection (Optional Feature)

The app includes an optional table detection feature using PaddleOCR:

- Module: `table_chunker.py`
- Checkbox: "Détection automatique des tableaux" (images only)
- When enabled:
  1. Detects tables in the image using PPStructureV3
  2. Crops each table with padding
  3. Applies upscaling for better quality
  4. Processes each table separately through Mistral OCR
  5. Validates results (stable column count, plausible values)
  6. Identifies table type (chemistry, mechanical, generic)

**Important**: This feature is memory-intensive and may not work on Render's free tier (512MB RAM limit). The app will gracefully fall back to standard OCR if PaddleOCR initialization fails.

### Render Deployment Issues

**PaddleOCR Memory Constraints:**
- PaddleOCR models (~10 models, several GB) are very memory-intensive
- Render free tier (512MB RAM) may kill the process with SIGTERM during initialization
- Optimizations applied:
  - `use_angle_cls=False` - disables angle classification
  - `lang='en'` - uses English-only models (lighter than multi-language)
  - `use_gpu=False` - forces CPU mode
- Consider upgrading to Render's paid tier (more RAM) if table detection is required

**Workarounds:**
1. Disable table detection checkbox for production use on free tier
2. Upgrade to Render's Starter plan or higher (2GB+ RAM)
3. Use alternative deployment platform with more resources (AWS, GCP, Azure)
