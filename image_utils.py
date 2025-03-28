"""
Utility functions for handling images in different formats
"""

import io
from PIL import Image

# Try to import pillow-heif for HEIC support
try:
    from pillow_heif import register_heif_opener
    # Register the HEIF opener with Pillow
    register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False

def open_image(file_or_path):
    """
    Open an image file in various formats including WEBP and HEIC
    
    Args:
        file_or_path: A file-like object or path to an image file
    
    Returns:
        PIL.Image: The opened image
    
    Raises:
        Exception: If the image cannot be opened
    """
    # First try standard PIL.Image.open
    try:
        image = Image.open(file_or_path)
        # Force load the image to make sure it's valid
        image.load()
        return image
    except Exception as e:
        # If we have HEIF support and standard open failed, maybe it's a special format
        if HEIF_SUPPORT:
            try:
                # Try again, now with HEIF registration in place
                image = Image.open(file_or_path)
                image.load()
                return image
            except Exception as heif_e:
                raise Exception(f"לא ניתן לפתוח את הקובץ: {str(e)}. נסיון HEIF נכשל: {str(heif_e)}")
        else:
            raise Exception(f"לא ניתן לפתוח את הקובץ: {str(e)}. תמיכה בפורמט HEIC/HEIF לא זמינה.")
