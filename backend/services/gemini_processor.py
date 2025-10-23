import os
import json
import logging
from typing import Optional
import google.generativeai as genai
from models.schemas import GeminiProcessingResult, GeminiParsedData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GENAI_API_KEY"))


async def process_balance_sheet_pdf(
    pdf_bytes: bytes,
    entity_name: str
) -> GeminiProcessingResult:
    """
    Process a PDF balance sheet using Google Gemini 2.5 Flash.
    
    Args:
        pdf_bytes: Raw PDF file bytes
        entity_name: Name of the main entity being processed
    
    Returns:
        GeminiProcessingResult with parsed data or error
    """
    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # Craft the prompt for Gemini
        prompt = """You are a financial data extraction expert. Extract structured financial data from this balance sheet PDF.

The main company is: """ + entity_name + """

Return ONLY valid JSON (no markdown, no code blocks, no extra text) with this exact structure:

{
  "entity": {
    "name": "company_name",
    "fiscal_year": 2024,
    "fiscal_period": "Annual or Q1 or Q2 or Q3 or Q4"
  },
  "subsidiaries": [
    {
      "name": "Subsidiary Name",
      "parent": "Parent Company Name"
    }
  ],
  "line_items": [
    {
      "subsidiary": "Entity Name",
      "section": "assets or liabilities or equity or income or cashflow",
      "line_name": "Line Item Name",
      "value": 1000.50,
      "currency": "INR"
    }
  ]
}

EXTRACTION RULES:
1. Extract ALL line items from Balance Sheet, Income Statement, and Cash Flow
2. For each subsidiary listed in consolidated financials, create an entry
3. Include parent company standalone items with subsidiary = main company name
4. Keep values as numbers only (no currency symbols or commas)
5. Valid sections: "assets", "liabilities", "equity", "income", "cashflow"
6. If parent is not explicit, assume parent = """ + entity_name + """

Return ONLY the JSON object, nothing else."""
        
        logger.info(f"Sending PDF to Gemini for entity: {entity_name}")
        
        # Send PDF to Gemini
        response = model.generate_content([
            {
                "mime_type": "application/pdf",
                "data": pdf_bytes
            },
            prompt
        ])
        
        raw_response = response.text
        logger.info(f"Received response from Gemini (length: {len(raw_response)})")
        
        # Parse the JSON response
        parsed_json = _extract_json_from_response(raw_response)
        
        if not parsed_json:
            logger.error("Could not extract JSON from Gemini response")
            return GeminiProcessingResult(
                success=False,
                data=None,
                error="Could not extract valid JSON from Gemini response",
                raw=raw_response
            )
        
        # Validate the structure
        validated_data = _validate_parsed_data(parsed_json)
        
        if not validated_data:
            logger.error("Parsed data validation failed")
            return GeminiProcessingResult(
                success=False,
                data=None,
                error="Parsed data does not match expected structure",
                raw=raw_response
            )
        
        logger.info(f"Successfully processed PDF: {len(validated_data.line_items)} items extracted")
        
        return GeminiProcessingResult(
            success=True,
            data=validated_data,
            error=None,
            raw=raw_response
        )
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return GeminiProcessingResult(
            success=False,
            data=None,
            error=f"JSON parsing error: {str(e)}",
            raw=None
        )
    
    except Exception as e:
        logger.error(f"Unexpected error during processing: {str(e)}")
        return GeminiProcessingResult(
            success=False,
            data=None,
            error=f"Processing error: {str(e)}",
            raw=None
        )


def _extract_json_from_response(response_text: str) -> Optional[dict]:
    """
    Extract JSON from Gemini response (handles markdown code blocks).
    
    Args:
        response_text: Raw text from Gemini
    
    Returns:
        Parsed JSON dict or None
    """
    
    # Remove markdown code blocks if present
    text = response_text.strip()
    
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
    
    if text.endswith("```"):
        text = text[:-3]  # Remove trailing ```
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in response
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            try:
                return json.loads(text[start_idx:end_idx+1])
            except json.JSONDecodeError:
                return None
        
        return None


def _validate_parsed_data(data: dict) -> Optional[GeminiParsedData]:
    """
    Validate and convert parsed JSON to GeminiParsedData model.
    
    Args:
        data: Raw parsed JSON dictionary
    
    Returns:
        GeminiParsedData or None if validation fails
    """
    
    try:
        # Ensure required top-level keys exist
        if "entity" not in data or "subsidiaries" not in data or "line_items" not in data:
            logger.error("Missing required top-level keys")
            return None
        
        # Validate entity
        entity = data.get("entity", {})
        if not isinstance(entity, dict):
            logger.error("Entity is not a dictionary")
            return None
        
        # Validate subsidiaries
        subsidiaries = data.get("subsidiaries", [])
        if not isinstance(subsidiaries, list):
            logger.error("Subsidiaries is not a list")
            return None
        
        # Validate line items
        line_items = data.get("line_items", [])
        if not isinstance(line_items, list):
            logger.error("Line items is not a list")
            return None
        
        # Filter out invalid line items
        valid_line_items = []
        for item in line_items:
            if _is_valid_line_item(item):
                valid_line_items.append(item)
            else:
                logger.warning(f"Skipping invalid line item: {item}")
        
        if not valid_line_items:
            logger.warning("No valid line items found after filtering")
        
        # Create and return GeminiParsedData
        parsed_data = GeminiParsedData(
            entity=entity,
            subsidiaries=subsidiaries,
            line_items=valid_line_items
        )
        
        return parsed_data
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return None


def _is_valid_line_item(item: dict) -> bool:
    """
    Check if a line item has required fields.
    
    Args:
        item: Line item dictionary
    
    Returns:
        True if valid, False otherwise
    """
    
    required_fields = ["subsidiary", "section", "line_name", "value"]
    
    # Check all required fields exist
    for field in required_fields:
        if field not in item:
            logger.warning(f"Line item missing field: {field}")
            return False
    
    # Validate section is one of allowed values
    valid_sections = ["assets", "liabilities", "equity", "income", "cashflow"]
    if item.get("section") not in valid_sections:
        logger.warning(f"Invalid section: {item.get('section')}")
        return False
    
    # Validate value is numeric
    try:
        value = item.get("value")
        if isinstance(value, (int, float)):
            return True
        float(value)  # Try to convert to float
        return True
    except (ValueError, TypeError):
        logger.warning(f"Invalid value: {item.get('value')}")
        return False