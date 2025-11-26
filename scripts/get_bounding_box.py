#!/usr/bin/env python3
"""
Extract bounding box dimensions from PDF figure
"""

import sys
from decimal import Decimal, ROUND_HALF_UP
import pdfplumber
from pypdf import PdfReader

def get_pdf_dimensions(pdf_path):
    """Extract page size and object bounding boxes from PDF"""
    
    # Get page dimensions using pypdf
    reader = PdfReader(pdf_path)
    page = reader.pages[0]
    
    # Get MediaBox (page dimensions in points, 1 point = 1/72 inch)
    mediabox = page.mediabox
    page_width = float(mediabox.width)
    page_height = float(mediabox.height)
    
    print("=" * 60)
    print("PDF PAGE DIMENSIONS")
    print("=" * 60)
    print(f"Page Width:  {page_width:.2f} points = {page_width/72:.2f} inches = {page_width/72*25.4:.2f} mm")
    print(f"Page Height: {page_height:.2f} points = {page_height/72:.2f} inches = {page_height/72*25.4:.2f} mm")
    print()
    
    # Use pdfplumber to extract objects
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        
        # Get all curves/lines (the drawing paths)
        curves = first_page.curves
        rects = first_page.rects
        lines = first_page.lines
        
        print("=" * 60)
        print("OBJECTS FOUND")
        print("=" * 60)
        print(f"Curves/Paths: {len(curves)}")
        print(f"Rectangles:   {len(rects)}")
        print(f"Lines:        {len(lines)}")
        print()
        
        # Calculate bounding box of all drawing objects
        if curves or lines or rects:
            all_objects = []
            
            # Collect all coordinates
            for curve in curves:
                all_objects.append((curve['x0'], curve['top']))
                all_objects.append((curve['x1'], curve['bottom']))
            
            for line in lines:
                all_objects.append((line['x0'], line['top']))
                all_objects.append((line['x1'], line['bottom']))
                
            for rect in rects:
                all_objects.append((rect['x0'], rect['top']))
                all_objects.append((rect['x1'], rect['bottom']))
            
            if all_objects:
                x_coords = [obj[0] for obj in all_objects]
                y_coords = [obj[1] for obj in all_objects]
                
                min_x = min(x_coords)
                max_x = max(x_coords)
                min_y = min(y_coords)
                max_y = max(y_coords)
                
                bbox_width = max_x - min_x
                bbox_height = max_y - min_y
                
                print("=" * 60)
                print("BOUNDING BOX OF FIGURE")
                print("=" * 60)
                print(f"X range: {min_x:.2f} to {max_x:.2f}")
                print(f"Y range: {min_y:.2f} to {max_y:.2f}")
                print()
                print(f"WIDTH:  {bbox_width:.2f} points = {bbox_width/72:.2f} inches = {bbox_width/72*25.4:.2f} mm")
                print(f"HEIGHT: {bbox_height:.2f} points = {bbox_height/72:.2f} inches = {bbox_height/72*25.4:.2f} mm")
                print()
                print("=" * 60)
                print("SUMMARY")
                print("=" * 60)
                print(f"Figure Width:  {bbox_width:.2f} pt | {bbox_width/72:.4f} in | {bbox_width/72*25.4:.2f} mm")
                print(f"Figure Height: {bbox_height:.2f} pt | {bbox_height/72:.4f} in | {bbox_height/72*25.4:.2f} mm")
                print(f"Aspect Ratio:  {bbox_width/bbox_height:.3f}")
                
                return bbox_width, bbox_height

def get_bounding_box_mm(pdf_path):
    """
    Get bounding box width and height in millimeters.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        tuple: (width_mm, height_mm) - Width and height in millimeters
               Returns (None, None) if no objects found
    """
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        
        # Get all curves/lines/rectangles (the drawing paths)
        curves = first_page.curves
        rects = first_page.rects
        lines = first_page.lines
        
        # Calculate bounding box of all drawing objects
        if curves or lines or rects:
            all_objects = []
            
            # Collect all coordinates
            for curve in curves:
                all_objects.append((curve['x0'], curve['top']))
                all_objects.append((curve['x1'], curve['bottom']))
            
            for line in lines:
                all_objects.append((line['x0'], line['top']))
                all_objects.append((line['x1'], line['bottom']))
                
            for rect in rects:
                all_objects.append((rect['x0'], rect['top']))
                all_objects.append((rect['x1'], rect['bottom']))
            
            if all_objects:
                x_coords = [obj[0] for obj in all_objects]
                y_coords = [obj[1] for obj in all_objects]
                
                min_x = min(x_coords)
                max_x = max(x_coords)
                min_y = min(y_coords)
                max_y = max(y_coords)
                
                # Calculate width and height in points
                bbox_width_pt = max_x - min_x
                bbox_height_pt = max_y - min_y
                
                # Convert to millimeters (1 point = 1/72 inch, 1 inch = 25.4 mm)
                # Use Decimal with 1 decimal place precision
                width_mm = (Decimal(str(bbox_width_pt)) / Decimal('72')) * Decimal('25.4')
                height_mm = (Decimal(str(bbox_height_pt)) / Decimal('72')) * Decimal('25.4')
                
                # Round to 1 decimal place
                width_mm = width_mm.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
                height_mm = height_mm.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
                
                return float(width_mm), float(height_mm)
    
    return None, None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./scripts/get_bounding_box.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    get_pdf_dimensions(pdf_path)