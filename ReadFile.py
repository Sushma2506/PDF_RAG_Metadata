from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx import Presentation
import os
import sys
import pdfplumber
from bs4 import BeautifulSoup
import docx
import pandas as pd
from PIL import Image
import fitz  # PyMuPDF for PDF images

# Reconfigure stdout to handle utf-8 characters properly in Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:\Users\saira\Downloads\SAU-I-983-Instructions.pptx"

def ensure_dir(directory):
    """Create directory if it doesn't exist"""
    os.makedirs(directory, exist_ok=True)

def read_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    img_dir = f"{base_name}_images"
    ensure_dir(img_dir)
    
    if file_path.lower().endswith('.pdf'):
        # PDF - PyMuPDF for images + pdfplumber for tables/text
        text = ""
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += f"\n--- PAGE {page_num + 1} ---\n"
            text += page.get_text("text") + "\n"
            
            # Extract images
            image_list = page.get_images(full=True)
            for img_idx, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                img_path = os.path.join(img_dir, f"pdf_page{page_num+1}_img{img_idx+1}.{image_ext}")
                with open(img_path, 'wb') as img_file:
                    img_file.write(image_bytes)
                text += f"[IMAGE SAVED: {img_path}]\n"
        
        # Tables with pdfplumber (secondary pass)
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if tables:
                    for table_num, table in enumerate(tables, start=1):
                        if table and len(table) > 1:
                            try:
                                df = pd.DataFrame(table[1:], columns=table[0])
                                text += f"\n[TABLE {page_num}-{table_num}]\n{df.to_string()}\n[/TABLE]\n"
                            except:
                                text += f"[TABLE {page_num}-{table_num} DETECTED]\n"
        
        doc.close()
        return text
        
    elif file_path.lower().endswith('.docx'):
        doc = docx.Document(file_path)
        text = ""
        
        # Text + Tables
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text.strip() + "\n"
        
        for table_idx, table in enumerate(doc.tables, start=1):
            text += f"\n[TABLE {table_idx}]\n"
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                text += " | ".join(cells) + "\n"
            text += "[/TABLE]\n"
        
        # EXTRACT IMAGES
        for i, image_part in enumerate(doc.part.blip_store.image_parts):
            image_bytes = image_part.blob
            image_extension = image_part.content_type.split('/')[-1]
            img_path = os.path.join(img_dir, f"doc_img_{i+1}.{image_extension}")
            
            with open(img_path, 'wb') as f:
                f.write(image_bytes)
            text += f"[IMAGE SAVED: {img_path}]\n"
        
        return text
        
    elif file_path.lower().endswith('.pptx'):
        prs = Presentation(file_path)
        text = ""
        
        for slide_num, slide in enumerate(prs.slides, start=1):
            text += f"\n--- SLIDE {slide_num} ---\n"
            
            for shape_idx, shape in enumerate(slide.shapes):
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        if paragraph.text.strip():
                            text += paragraph.text.strip() + "\n"
                elif shape.has_table:
                    text += "[TABLE]\n"
                    table = shape.table
                    for row in table.rows:
                        cells = [cell.text.strip() for cell in row.cells]
                        text += " | ".join(cells) + "\n"
                    text += "[/TABLE]\n"
                elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    # Extract PPTX images
                    image_obj = shape.image
                    image_bytes = image_obj.blob
                    image_extension = image_obj.content_type.split('/')[-1]
                    img_path = os.path.join(img_dir, f"ppt_slide{slide_num}_img{shape_idx}.{image_extension}")
                    
                    with open(img_path, 'wb') as f:
                        f.write(image_bytes)
                    text += f"[IMAGE SAVED: {img_path}]\n"
                elif shape.shape_type == MSO_SHAPE_TYPE.CHART:
                    text += "[CHART DETECTED]\n"
        
        return text
        
    elif file_path.lower().endswith(('.html', '.htm')):
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # Download external images
        for img_num, img in enumerate(soup.find_all('img'), start=1):
            src = img.get('src', '')
            alt = img.get('alt', f'image {img_num}')
            
            if src.startswith('http'):
                try:
                    import requests
                    response = requests.get(src, timeout=5)
                    img_extension = response.headers.get('content-type', '').split('/')[-1] or 'jpg'
                    img_path = os.path.join(img_dir, f"html_img_{img_num}.{img_extension}")
                    
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    text += f"[IMAGE SAVED: {img_path}]\n"
                except:
                    text += f"[IMAGE: {alt} | {src} (failed to download)]\n"
            else:
                text += f"[IMAGE: {alt} | {src}]\n"
        return text
        
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except:
            return f"[ERROR: Could not read {os.path.basename(file_path)}]"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(read_file(sys.argv[1]))
    elif os.path.exists(file_path):
        print(f"Reading default file: {file_path}")
        print(f"Images will be saved to: {os.path.join(os.path.dirname(file_path), f'{os.path.splitext(os.path.basename(file_path))[0]}_images')}")
        print("="*80)
        print(read_file(file_path))
    else:
        print("Usage: python ReadFile.py <path_to_file>")
