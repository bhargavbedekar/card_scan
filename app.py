import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import easyocr
from transformers import pipeline
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os

# Ensure pytesseract path is correct for your system
pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Initialize Hugging Face NER pipeline
ner_pipeline = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")


# Hybrid OCR function combining EasyOCR and Tesseract
def extract_text_combined(image):
    easyocr_text = extract_text_easyocr(image)
    tesseract_text = extract_text_tesseract(image)

    # Merge the results from both methods
    combined_text = f"{easyocr_text} {tesseract_text}".strip()
    return combined_text


# Preprocessing function with adaptive thresholding
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    # Adaptive thresholding for better text extraction
    binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    return binary


# Text extraction using EasyOCR
def extract_text_easyocr(image):
    results = reader.readtext(image)
    return ' '.join([result[1] for result in results])


# Text extraction using Tesseract
def extract_text_tesseract(image):
    text = pytesseract.image_to_string(image, config='--psm 6')  # PSM 6 for block of text
    return text


# Information extraction using NER and regular expressions
def extract_info(text):
    # Use NER to identify entities
    ner_results = ner_pipeline(text)

    info = {
        'name': extract_name(ner_results, text),
        'job_title': extract_job_title(text),
        'email': extract_email(text),
        'phone': extract_phone(text),
        'website': extract_website(text),
        'address': extract_address(ner_results, text),
        'company': extract_company(ner_results, text)
    }
    return info


# Name extraction using NER and fallback regex
def extract_name(ner_results, text):
    person_entities = [entity for entity in ner_results if entity['entity_group'] == 'PER']
    if person_entities:
        return ' '.join([entity['word'] for entity in person_entities])

    # Fallback regex for names
    name_pattern = r'(?:Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)?\s?([A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]+)'
    matches = re.findall(name_pattern, text)
    return matches[0] if matches else ''


# Job title extraction using regex
def extract_job_title(text):
    job_title_pattern = r'(MANAGING DIRECTOR|CEO|CTO|CFO|COO|President|Vice President|Manager|Director|Engineer|Consultant|Analyst|Associate)'
    matches = re.findall(job_title_pattern, text, re.IGNORECASE)
    return matches[0] if matches else ''


# Email extraction using regex
def extract_email(text):
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    return matches[0] if matches else ''


# Phone extraction using regex
def extract_phone(text):
    phone_pattern = r'\+?1?\s*\(?-*\.*(\d{3})\)?\.*-*\s*(\d{3})\.*-*\s*(\d{4})'
    matches = re.findall(phone_pattern, text)
    return '-'.join(matches[0]) if matches else ''


# Website extraction using regex
def extract_website(text):
    website_pattern = r'(?:https?:\/\/)?(?:www\.)?([A-Za-z0-9-]+\.[A-Za-z]{2,})(?:\/[A-Za-z0-9-._~:/?#[\]@!$&\'()*+,;=]*)?'
    matches = re.findall(website_pattern, text.lower())
    return matches[0] if matches else ''


# Address extraction using NER and fallback regex
def extract_address(ner_results, text):
    loc_entities = [entity for entity in ner_results if entity['entity_group'] == 'LOC']
    if loc_entities:
        return ' '.join([entity['word'] for entity in loc_entities])

    # Fallback regex for address
    address_pattern = r'\d{1,5}\s\w+\s\w+\.?,?\s\w+\s\w+'
    matches = re.findall(address_pattern, text)
    return matches[0] if matches else ''


# Company extraction using NER and fallback regex
def extract_company(ner_results, text):
    org_entities = [entity for entity in ner_results if entity['entity_group'] == 'ORG']
    if org_entities:
        return ' '.join([entity['word'] for entity in org_entities])

    # Fallback regex for company names
    company_pattern = r'\b([A-Z]+(?:\s[A-Z]+)*)\b'
    matches = re.findall(company_pattern, text)
    return max(matches, key=len) if matches else ''


# Email sending function
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os

def send_email(recipient_email, subject, message_body, signature_image=None):
    sender_email = "tss@techservesolutions.in"
    sender_password = "gjas koww hiuz kktj"  # Use your Google Workspace App Password

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Create a message with HTML content
    if signature_image and os.path.isfile(signature_image):
        with open(signature_image, 'rb') as img_file:
            img = MIMEImage(img_file.read())
            img.add_header('Content-ID', '<signature_image>')  # Assign a content ID to reference in HTML
            msg.attach(img)

        # Update message body to include the signature image
        message_body += f'<br><img src="cid:signature_image">'  # Embed the image in the message body

    # Attach the main message body in HTML format
    msg.attach(MIMEText(message_body, 'html'))

    try:
        # Gmail SMTP server setup
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")



# Main function for the Streamlit app
def main():
    st.title("Advanced Business Card Scanner")

    uploaded_file = st.file_uploader("Choose a business card image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='Uploaded Business Card', use_column_width=True)

        image_np = np.array(image)
        preprocessed = preprocess_image(image_np)

        # Extract text using both EasyOCR and Tesseract
        full_text = extract_text_combined(preprocessed)

        # Extract structured information
        info = extract_info(full_text)

        st.subheader("Extracted Information:")
        for key, value in info.items():
            if value:
                st.write(f"{key.capitalize()}: {value}")

        st.subheader("Raw Extracted Text:")
        st.text(full_text)

        # Check if email is extracted and provide an option to send an email
        if info['email']:
            st.subheader("Send an Email")
            subject = st.text_input("Email Subject", "Thank you for connecting!")
            message_body = (
                "Hello 你好 Tss,<br><br>"
                "Nice to See you at Canton Fair Oct 2024 很高興在廣州見到你<br><br>"
                "We are interested in buying your products 我們有興趣購買你們的產品<br><br>"
                "Please send your product details as below 請發送您的產品詳細資訊如下<br><br>"
                "- Product Catalogue - 產品目錄<br>"
                "- Product Specifications, Dimensions, Weight and available color - 產品規格、尺寸、重量和可用顏色<br>"
                "- Product Packing and Master Box Details - 產品包裝​​和主盒詳細信息<br>"
                "- Minimum Order Quantity - 最小訂購量<br>"
                "- FOB China Port Price - FOB中國​​港口價格<br>"
                "- Delivery Period - 交貨期<br><br>"
                "Looking forward to have business with your company. 期待與貴公司開展業務<br><br>"
                "We will reply back to you after 29 Oct 2024 - 我們將在2024年10月29日後回覆您"
            )

            signature_image = "signature_image.png"  # Replace with the correct path to your signature image
            if st.button("Send Email"):
                send_email(info['email'], subject, message_body, signature_image)
                st.success(f"Email sent to {info['email']}")


if __name__ == "__main__":
    main()
