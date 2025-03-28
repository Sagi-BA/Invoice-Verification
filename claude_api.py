"""
Claude API handler for invoice verification system.
This module handles all interactions with the Anthropic Claude API.
"""

try:
    import requests
except ImportError:
    print("Error: requests module not installed. Please install it using 'pip install requests'")
    # Provide a fallback implementation if possible, or exit gracefully
    
import json
import base64
from PIL import Image
import io
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_system_prompt():
    """Return the system prompt for invoice verification."""
    return """**הגדרת תפקיד / אישיות:**
אתה מבקר פנימי בארגון, האחראי לוודא שכל החשבוניות המוגשות עומדות בסטנדרטים של חוקיות, ניהול תקין, טוהר המידות, חיסכון ויעילות. תפקידך כולל בדיקת התאמת החתימות על החשבוניות למורשי החתימה המאושרים, בהתאם לסכומים המצוינים. מטרתך היא להבטיח שכל התהליכים הכספיים בארגון מתבצעים בהתאם למדיניות ולנהלים הפנימיים.
**רקע / הקשר:**
בארגון קיימת מדיניות ברורה לגבי אישור חשבוניות:
* לכל מורשה חתימה מוגדר סכום מקסימלי לאישור.
* חשבוניות חייבות להכיל חתימה ברורה של מורשה חתימה.
* יש לוודא שהחתימה על החשבונית תואמת למורשה החתימה המאושר ולסכום המצויין.
כמבקר פנימי, עליך לבדוק את התאמת החתימה לסכום החשבונית ולוודא שהחתימה שייכת למורשה המתאים.
**הנחיות נוספות:**
* בעת בדיקת חשבוניות, הצג ניתוח בפורמט הבא:
  1. סכום החשבונית שנמצא
  2. שם מלא של מורשה החתימה שזוהה (אם זוהה)
  3. סטטוס בדיקה - חייב להיות אחד מאלה:
     - "תקין" - במקרה שהחתימה מזוהה והסכום תואם להרשאה
     - "לא תקין" - במקרה שהחתימה אינה מזוהה או שהסכום גבוה מההרשאה
     - "לא ברור" - במקרה שלא ניתן לקבוע בוודאות
* חשוב לציין בדיוק איפה בתמונה נמצאת החתימה ולתאר אותה בקצרה.
* יש לציין בפירוש "סטטוס: תקין" או "סטטוס: לא תקין" או "סטטוס: לא ברור" כדי שהמערכת תוכל לזהות את הסטטוס באופן אוטומטי."""

    # return """**הגדרת תפקיד:** 
    #     אתה מבקר פנימי בארגון, האחראי לוודא שחשבוניות עומדות בסטנדרטים של ניהול תקין ותואמות את הרשאות החתימה.

    #     **רקע:** 
    #     לכל מורשה חתימה יש סכום מקסימלי לאישור. עליך לבדוק את התאמת החתימה לסכום החשבונית.

    #     **פורמט דיווח:**
    #     הצג תשובה קצרה ומדויקת הכוללת אך ורק:
    #     * 1. סכום החשבונית: [הסכום בש"ח]
    #     * 2. מורשה חתימה: [שם מלא של מורשה החתימה שזוהה]
    #     * 3. סטטוס: [תקין/לא תקין/לא ברור] - [סיבה קצרה במקרה הצורך]

    #     אין לחזור על המידע או להוסיף הסברים מעבר למבוקש."""

def encode_image(image):
    """
    Convert an image to base64 encoding for API transmission.
    Handles RGBA conversion to RGB for JPEG encoding.
    """
    buffered = io.BytesIO()
    
    # Convert RGBA images to RGB before encoding as JPEG
    if image.mode == 'RGBA':
        image = image.convert('RGB')
        
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def call_claude_api(api_key, invoice_image, signatories, signature_images):
    """
    Call the Claude API to verify an invoice.
    
    Args:
        api_key (str): Anthropic API key
        invoice_image (PIL.Image): The invoice image to verify
        signatories (dict): Dictionary of authorized signatories and their max amounts
        signature_images (dict): Dictionary of signature reference images
        
    Returns:
        dict: The API response or error information
    """
    url = "https://api.anthropic.com/v1/messages"
    
    # Format signatories info
    signatories_info = "רשימת מורשי החתימה:\n"
    for name, amount in signatories.items():
        signatories_info += f"- {name}: עד {amount} ש״ח\n"
    
    # Create content items starting with text
    content_items = [
        {
            "type": "text", 
            "text": f"אנא בדוק את החשבונית הזו. האם היא עומדת בכל הדרישות?\n\nחשוב מאוד: סכם את הבדיקה עם שורה אחת בלבד בפורמט הבא: STATUS: [תקין/לא תקין/לא ברור]\n\n{signatories_info}"
            # "text": f"אנא בדוק את החשבונית הזו. האם היא עומדת בכל הדרישות?\n\n{signatories_info}"
        }
    ]
    
    # Add invoice image
    try:
        invoice_base64 = encode_image(invoice_image)
        content_items.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": invoice_base64
            }
        })
    except Exception as e:
        return {"error": f"שגיאה בקידוד תמונת החשבונית: {str(e)}"}
    
    # Add signature reference images if available
    for name, sig_image in signature_images.items():
        if sig_image is not None:
            try:
                content_items.append({
                    "type": "text",
                    "text": f"דוגמת חתימה של {name}:"
                })
                signature_base64 = encode_image(sig_image)
                content_items.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": signature_base64
                    }
                })
            except Exception as e:
                # Continue even if one signature fails to encode
                print(f"Warning: Failed to encode signature for {name}: {e}")
    
    # Headers
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Data payload
    data = {
        "model": "claude-3-7-sonnet-20250219", #"claude-3-5-sonnet-20240620"
        "system": get_system_prompt(),
        "max_tokens": 1000,
        "temperature": 0,  # Set to 0 for deterministic responses
        "messages": [
            {
                "role": "user",
                "content": content_items
            }
        ]
    }
    
    # Make the API call
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()  # Raise an exception for HTTP errors
        response_data = response.json()
        
        # Extract Claude's text response
        result_text = ""
        status_code = "unclear"  # Default status
        
        # print("Response Data:", response_data)  # Debugging line

        if "content" in response_data:
            for item in response_data["content"]:
                if item["type"] == "text":
                    result_text += item["text"]
            
            # Parse the status from the response
            if "STATUS: תקין" in result_text:
                status_code = "valid"
            elif "STATUS: לא תקין" in result_text:
                status_code = "invalid"
            elif "STATUS: לא ברור" in result_text:
                status_code = "unclear"
            
        # Add the status code to the response
        response_data["status_code"] = status_code
        
        return response_data
        
    except requests.exceptions.RequestException as e:
        return {
            "error": f"שגיאה בשליחת הבקשה לAPI: {str(e)}",
            "status": "error",
            "status_code": "error"
        }
    except json.JSONDecodeError:
        return {
            "error": f"שגיאה בקריאת תשובת API",
            "status": "error",
            "status_code": "error"
        }

def get_api_key():
    """
    Get the Anthropic API key from environment variables.
    Returns API key or None if not found.
    """
    return os.getenv("ANTHROPIC_API_KEY")