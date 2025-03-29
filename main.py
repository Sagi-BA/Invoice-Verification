import streamlit as st

# Set page config (MUST be the first Streamlit command)
st.set_page_config(
    page_title="מערכת אימות חשבוניות",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

import requests
import json
import base64
import os
import pathlib
import glob
from PIL import Image
import io
from dotenv import load_dotenv

# Import our Claude API handler
import claude_api

# Load environment variables from .env file
load_dotenv()

# Constants
SIGNATORIES_FILE = "authorized_signatories.json"
SIGNATURES_DIR = "signatures"
BACKUPS_DIR = "backups"
SAMPLE_INVOICES_DIR = "invoice"  # Directory for sample invoices

# Ensure directories exist
os.makedirs(SIGNATURES_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)
os.makedirs(SAMPLE_INVOICES_DIR, exist_ok=True)  # Create sample invoice directory if it doesn't exist

# Function to get sample invoices
def get_sample_invoices():
    """Get list of sample invoice files from the invoice directory"""
    samples = []
    
    # Get all image files in the invoice directory
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.heic', '*.heif']:
        pattern = os.path.join(SAMPLE_INVOICES_DIR, ext)
        samples.extend(glob.glob(pattern))
    
    # Sort files by name
    samples.sort()
    
    return samples

# Function to create backup of signatories file
def backup_signatories_file():
    if os.path.exists(SIGNATORIES_FILE):
        from datetime import datetime
        import shutil
        
        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{BACKUPS_DIR}/signatories_backup_{timestamp}.json"
        
        # Copy file to backup
        shutil.copy2(SIGNATORIES_FILE, backup_file)
        
        # Keep only the 5 most recent backups
        backups = sorted([f for f in os.listdir(BACKUPS_DIR) if f.startswith("signatories_backup_")])
        for old_backup in backups[:-5]:  # Remove all but the 5 newest
            try:
                os.remove(os.path.join(BACKUPS_DIR, old_backup))
            except:
                pass

# Function to safely open image files in various formats
def safe_open_image(file):
    try:
        image = Image.open(file)
        # For HEIC/HEIF images from iPhone, they might need conversion
        if hasattr(image, 'format') and image.format in ['HEIC', 'HEIF']:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
        return image
    except Exception as e:
        st.error(f"שגיאה בפתיחת הקובץ: {str(e)}")
        st.info("אם הקובץ הוא בפורמט HEIC (תמונה מאייפון), ייתכן שתצטרך להמירו ל-JPEG לפני העלאה.")
        return None

# Function to encode image to base64
def encode_image(image):
    buffered = io.BytesIO()
    
    # Convert RGBA images to RGB before encoding as JPEG
    if image.mode == 'RGBA':
        image = image.convert('RGB')
        
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Load authorized signatories from JSON file
def load_signatories():
    try:
        if os.path.exists(SIGNATORIES_FILE):
            with open(SIGNATORIES_FILE, 'r', encoding='utf-8') as f:
                signatories_data = json.load(f)
            
            # Convert to the format used in the app
            signatories = {}
            signature_images = {}
            missing_images = []
            
            for name, data in signatories_data.items():
                signatories[name] = data['max_amount']
                
                # Load signature image if available
                if 'signature_image_path' in data:
                    image_path = data['signature_image_path']
                    if os.path.exists(image_path):
                        try:
                            signature_images[name] = safe_open_image(image_path)
                        except Exception as e:
                            missing_images.append(f"{name} (שגיאה: {str(e)})")
                    else:
                        missing_images.append(f"{name} (קובץ לא נמצא: {image_path})")
            
            # Display warning for missing images
            if missing_images and len(missing_images) > 0:
                missing_list = "\n".join(missing_images)
                st.warning(f"לא ניתן היה לטעון את תמונות החתימה הבאות:\n{missing_list}")
            
            return signatories, signature_images
        return {}, {}
    except Exception as e:
        st.error(f"שגיאה בטעינת מורשי החתימה: {str(e)}")
        return {}, {}

# Save authorized signatories to JSON file
def save_signatories(signatories, signature_images):
    try:
        # Create backup before making changes
        backup_signatories_file()
        
        signatories_data = {}
        
        for name, amount in signatories.items():
            signatories_data[name] = {
                "max_amount": amount
            }
            
            # Save signature image if available
            if name in signature_images and signature_images[name] is not None:
                # Determine file extension based on image format
                img = signature_images[name]
                if img.mode == 'RGBA':
                    # PNG format for images with transparency
                    filename = f"{SIGNATURES_DIR}/{name.replace(' ', '_').replace('/', '_')}_signature.png"
                else:
                    # JPEG for RGB images
                    filename = f"{SIGNATURES_DIR}/{name.replace(' ', '_').replace('/', '_')}_signature.jpg"
                    # Convert to RGB if needed
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                
                # Save the image
                try:
                    img.save(filename)
                    signatories_data[name]["signature_image_path"] = filename
                except Exception as img_error:
                    # Try alternative format if saving fails
                    try:
                        alt_filename = f"{SIGNATURES_DIR}/{name.replace(' ', '_').replace('/', '_')}_signature.png"
                        img_rgb = img.convert('RGB')
                        img_rgb.save(alt_filename)
                        signatories_data[name]["signature_image_path"] = alt_filename
                    except:
                        st.warning(f"לא ניתן לשמור את תמונת החתימה של {name}: {str(img_error)}")
        
        # Write the JSON file
        with open(SIGNATORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(signatories_data, f, ensure_ascii=False, indent=2)
            
        return True
    except Exception as e:
        st.error(f"שגיאה בשמירת מורשי החתימה: {str(e)}")
        return False

# Set Anthropic API key - securely get from secrets
def get_api_key():
    # First try to get from environment variable via claude_api module
    api_key = claude_api.get_api_key()
    if api_key:
        return api_key
    
    # Then from streamlit secrets if deployed
    if 'ANTHROPIC_API_KEY' in st.secrets:
        return st.secrets['ANTHROPIC_API_KEY']
        
    # Otherwise get from session state or user input
    if 'api_key' not in st.session_state or not st.session_state.api_key:
        st.session_state.api_key = st.sidebar.text_input("Enter your Anthropic API Key:", type="password")
    return st.session_state.api_key

# Main app
def main():
    # Custom CSS for RTL support and styling
    st.markdown("""
    <style>
    .rtl {
        direction: rtl;
        text-align: right;
    }
    .stApp {
        font-family: 'Arial', sans-serif;
    }
    .result-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        direction: rtl;
        text-align: right;
    }
    .status-indicator {
        text-align: center;
        font-size: 2em;
        margin: 20px 0;
    }
    .status-icon {
        font-size: 4em;
        margin-bottom: 10px;
    }
    .green-status {
        color: #28a745;
    }
    .red-status {
        color: #dc3545;
    }
    .orange-status {
        color: #fd7e14;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.markdown("<h1 class='rtl'>מערכת אימות חשבוניות</h1>", unsafe_allow_html=True)
    
    # Initialize session state for signatories
    if 'signatories' not in st.session_state or 'signature_images' not in st.session_state:
        # Load from file
        signatories, signature_images = load_signatories()
        st.session_state.signatories = signatories
        st.session_state.signature_images = signature_images
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("הגדרות")
        
        # API Key
        api_key = get_api_key()
        
        st.subheader("ניהול מורשי חתימה")
        
        # Add or update signatory
        with st.expander("הוסף/עדכן מורשה חתימה"):
            # Create a list of existing names + option for new
            existing_names = list(st.session_state.signatories.keys())
            options = ["הוסף מורשה חדש"] + existing_names
            
            name_option = st.selectbox("בחר פעולה:", options)
            
            if name_option == "הוסף מורשה חדש":
                new_name = st.text_input("שם מורשה החתימה:", key="new_name")
                is_new = True
            else:
                new_name = name_option
                is_new = False
                st.info(f"עריכת מורשה קיים: {new_name}")
            
            # For existing signatory, show current amount as default
            default_amount = st.session_state.signatories.get(new_name, 0) if not is_new else 0
            new_amount = st.number_input("סכום מקסימלי לאישור (ש״ח):", 
                                         min_value=0, 
                                         value=default_amount,
                                         key="new_amount")
            
            # Show current signature if exists
            if not is_new and new_name in st.session_state.signature_images:
                st.image(st.session_state.signature_images[new_name], 
                        caption=f"חתימה נוכחית של {new_name}", 
                        width=150)
            
            new_signature = st.file_uploader("העלה דוגמת חתימה (אופציונלי):", 
                                             type=["jpg", "jpeg", "png", "webp", "heic", "heif"], 
                                             key="new_signature")
            
            button_label = "הוסף מורשה" if is_new else "עדכן מורשה"
            if st.button(button_label):
                if new_name and new_amount > 0:
                    # Update amount
                    st.session_state.signatories[new_name] = new_amount
                    
                    # Update signature if new one provided
                    if new_signature:
                        signature_image = safe_open_image(new_signature)
                        if signature_image:
                            st.session_state.signature_images[new_name] = signature_image
                            
                            # Save to file
                            if save_signatories(st.session_state.signatories, st.session_state.signature_images):
                                action_text = "נוסף" if is_new else "עודכן"
                                st.success(f"מורשה החתימה {new_name} {action_text} בהצלחה!")
                            else:
                                st.error("שגיאה בשמירת הנתונים")
                    else:
                        # Save even without new signature
                        if save_signatories(st.session_state.signatories, st.session_state.signature_images):
                            action_text = "נוסף" if is_new else "עודכן"
                            st.success(f"מורשה החתימה {new_name} {action_text} בהצלחה!")
                        else:
                            st.error("שגיאה בשמירת הנתונים")
                            
                    # Force refresh to update display
                    st.rerun()
        
        # Display current signatories
        st.subheader("מורשי חתימה נוכחיים:")
        if st.session_state.signatories:
            for name, amount in st.session_state.signatories.items():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"{name}")
                with col2:
                    st.write(f"עד {amount} ש״ח")
                with col3:
                    if st.button("הסר", key=f"remove_{name}"):
                        del st.session_state.signatories[name]
                        if name in st.session_state.signature_images:
                            del st.session_state.signature_images[name]
                        
                        # Save to file
                        save_signatories(st.session_state.signatories, st.session_state.signature_images)
                        st.rerun()
                
                if name in st.session_state.signature_images:
                    st.image(st.session_state.signature_images[name], caption=f"חתימה של {name}", width=150)
        else:
            st.info("אין מורשי חתימה. הוסף מורשה חתימה חדש.")
    
    # Main content
    st.markdown("<h2 class='rtl'>בדיקת חשבונית</h2>", unsafe_allow_html=True)
    
    # Initialize columns
    col1, col2 = st.columns(2)
    
    # Add session state variables
    if 'verification_result' not in st.session_state:
        st.session_state.verification_result = None
    if 'show_verification_modal' not in st.session_state:
        st.session_state.show_verification_modal = False
    if 'verification_in_progress' not in st.session_state:
        st.session_state.verification_in_progress = False
    if 'status_code' not in st.session_state:
        st.session_state.status_code = "unclear"
    
    # Function to close the dialog
    def close_dialog():
        st.session_state.show_verification_modal = False
        st.rerun()
    
    # Function to start verification
    def start_verification():
        st.session_state.verification_in_progress = True
        st.session_state.show_verification_modal = True
        st.rerun()
    
    with col1:
        st.markdown("<p class='rtl'>העלה חשבונית לבדיקה:</p>", unsafe_allow_html=True)
        
        # Add sample invoices option to the radio buttons
        invoice_source = st.radio("בחר מקור:", ["העלאת קובץ", "צילום מהמצלמה", "חשבוניות לדוגמה"], horizontal=True)
        
        invoice_image = None
        
        if invoice_source == "העלאת קובץ":
            invoice_file = st.file_uploader("העלה חשבונית:", type=["jpg", "jpeg", "png", "webp", "heic", "heif"])
            if invoice_file:
                invoice_image = safe_open_image(invoice_file)
                if invoice_image:
                    st.image(invoice_image, caption="החשבונית שהועלתה", use_container_width=True)
        
        elif invoice_source == "צילום מהמצלמה":
            camera_input = st.camera_input("צלם חשבונית")
            if camera_input:
                invoice_image = safe_open_image(camera_input)
                if invoice_image:
                    st.image(invoice_image, caption="החשבונית שצולמה", use_container_width=True)
        
        elif invoice_source == "חשבוניות לדוגמה":
            # Get sample invoice files
            sample_invoices = get_sample_invoices()
            
            if not sample_invoices:
                st.info("לא נמצאו חשבוניות לדוגמה בתיקיית 'invoice'. נא להוסיף קבצי חשבוניות לתיקייה.")
            else:
                # Extract file names for display in the selectbox
                sample_names = [os.path.basename(f) for f in sample_invoices]
                
                # Create a dropdown to select a sample invoice
                selected_sample = st.selectbox("בחר חשבונית לדוגמה:", sample_names)
                
                # Get the full path of the selected sample
                selected_path = os.path.join(SAMPLE_INVOICES_DIR, selected_sample)
                
                # Load the selected sample invoice
                try:
                    invoice_image = safe_open_image(selected_path)
                    if invoice_image:
                        st.image(invoice_image, caption=f"חשבונית לדוגמה: {selected_sample}", use_container_width=True)
                except Exception as e:
                    st.error(f"שגיאה בטעינת חשבונית לדוגמה: {str(e)}")
    
    # Verify button
    if st.session_state.signatories and invoice_image and api_key:
        if st.button("בדוק חשבונית", type="primary", on_click=start_verification):
            pass  # The on_click handler will handle this
    elif not st.session_state.signatories:
        st.warning("נא להוסיף לפחות מורשה חתימה אחד לפני בדיקת חשבוניות.")
    elif not invoice_image:
        st.info("נא להעלות חשבונית לבדיקה.")
    elif not api_key:
        st.warning("נא להזין מפתח API של Anthropic.")
    
    # Define dialog function with decorator
    @st.dialog("תוצאות בדיקת החשבונית")
    def show_verification_results():
        if st.session_state.verification_in_progress:
            # Display progress bar
            st.markdown("<p class='rtl'>מנתח את החשבונית... אנא המתן</p>", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            
            # Process the verification
            for percent_complete in range(0, 101, 10):
                progress_bar.progress(percent_complete)
                if percent_complete == 40:  # At 40%, start the actual API call
                    try:
                        response = claude_api.call_claude_api(
                            api_key=api_key,
                            invoice_image=invoice_image,
                            signatories=st.session_state.signatories,
                            signature_images=st.session_state.signature_images
                        )
                        
                        # print(f"API Response: {response}")
                        if "error" in response:
                            st.error(response["error"])
                            st.session_state.verification_result = f"<span style='color:red'>שגיאה: {response['error']}</span>"
                            st.session_state.status_code = "error"
                        else:
                            # Extract Claude's response
                            claude_response = response.get("content", [])
                            result_text = ""
                            for item in claude_response:
                                if item["type"] == "text":
                                    result_text += item["text"]
                            
                            # Store both the result text and status code
                            st.session_state.verification_result = result_text
                            st.session_state.status_code = response.get("status_code", "unclear")
                    except Exception as e:
                        st.error(f"שגיאה בתהליך האימות: {str(e)}")
                        st.session_state.verification_result = f"<span style='color:red'>שגיאה: {str(e)}</span>"
                        st.session_state.status_code = "error"
            
            # Mark verification as complete
            st.session_state.verification_in_progress = False
            st.rerun()
        
        elif st.session_state.verification_result:
            # Get the result text
            result_text = st.session_state.verification_result
            
            # print(f"Result Text: {result_text[:100]}")
            
            # Check for keywords in response text - This is our main detection method
            if "לא תקין" in result_text:
                status = "לא תקין"
                status_color = "red"
                status_icon = "⛔"
            elif "לא ברור" in result_text:
                status = "לא ברור"
                status_color = "orange"
                status_icon = "❓"
            else:
                # Default to "תקין" if none of the above
                status = "תקין"
                status_color = "green"
                status_icon = "✅"
            
            # Extract signatory name - look for names in json file
            signatory_name = "לא נמצא"
            if st.session_state.signatories:
                for name in st.session_state.signatories.keys():
                    if name in result_text:
                        signatory_name = name
                        break
            
            if "לא ניתן לזהות" or "לא זוהתה חתימה" in result_text:
                signatory_name = "לא נמצא"

            # Display status indicator
            st.markdown(f"""
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <div style="background-color: {status_color}; color: white; border-radius: 50%; width: 100px; height: 100px; 
                display: flex; justify-content: center; align-items: center; font-size: 50px; margin: 10px;">
                    {status_icon}
                </div>
            </div>
            <div style="text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; color: {status_color};">
                סטטוס: {status}
            </div>
            <div style="text-align: center; font-size: 20px; margin-bottom: 20px; color: {status_color};">
                מורשה חתימה: {signatory_name}
            </div>
            """, unsafe_allow_html=True)
            
            # Display the detailed result
            st.markdown(f"<div class='rtl result-box'>{result_text}</div>", unsafe_allow_html=True)
            
            # Close button
            if st.button("סגור", key="close_dialog_results"):
                st.session_state.show_verification_modal = False
                st.rerun()
    
    # Display verification dialog when needed
    if st.session_state.show_verification_modal:
        show_verification_results()

if __name__ == "__main__":
    main()