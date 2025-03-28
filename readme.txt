# מערכת אימות חשבוניות (Invoice Verification System)

A Streamlit application for verifying invoices against authorized signatories using Claude AI.

## Features

- Upload invoices via file upload or camera capture
- Manage authorized signatories and their maximum approval amounts
- Upload signature reference images for comparison
- Verify signatures and approval authority using Claude AI
- Hebrew RTL interface

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/invoice-verification-system.git
cd invoice-verification-system
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
   - Rename `.env.example` to `.env` 
   - Add your Anthropic API key to the `.env` file

## Usage

1. Run the Streamlit app:
```bash
streamlit run main.py
```

2. Open your browser and navigate to the local URL displayed in your terminal (typically http://localhost:8501)

3. Add at least one authorized signatory in the sidebar

4. Upload an invoice image or capture one with your camera

5. Click "Check Invoice" to analyze the invoice

## Project Structure

- `main.py` - Main Streamlit application
- `.env` - Environment variables (API keys)
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.8+
- Anthropic API key (Claude 3.7 Sonnet or similar)
