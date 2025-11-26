"""
Async tasks for file conversion using CloudConvert API
"""
import os
import threading
import time
import requests
from django.conf import settings
from django.core.files.base import ContentFile


def convert_cdr_to_pdf_async(caja_id, cdr_file_path):
    """
    Asynchronously convert CDR file to PDF using CloudConvert API.
    
    Args:
        caja_id: ID of the Caja instance to update
        cdr_file_path: Path to the CDR file to convert (relative to MEDIA_ROOT)
    """
    thread = threading.Thread(
        target=convert_cdr_to_pdf,
        args=(caja_id, cdr_file_path),
        daemon=True
    )
    thread.start()


def convert_cdr_to_pdf(caja_id, cdr_file_path):
    """
    Convert CDR file to PDF using CloudConvert API and save to Caja instance.
    
    Args:
        caja_id: ID of the Caja instance to update
        cdr_file_path: Path to the CDR file to convert (relative to MEDIA_ROOT)
    """
    from .models import Caja
    
    try:
        # Get CloudConvert API key from settings
        api_key = getattr(settings, 'CLOUDCONVERT_API_KEY', None)
        if not api_key:
            print(f"Error: CLOUDCONVERT_API_KEY not configured in settings")
            return
        
        # Get the full path to the CDR file
        # cdr_file_path should already be an absolute path from Django's FileField.path
        cdr_file_full_path = None
        
        if os.path.isabs(cdr_file_path):
            # If absolute path provided, use it directly
            if os.path.exists(cdr_file_path):
                cdr_file_full_path = cdr_file_path
            else:
                # Try to extract filename and search in legacy location
                filename = os.path.basename(cdr_file_path)
                base_dir = getattr(settings, 'BASE_DIR', None)
                if base_dir:
                    legacy_path = os.path.join(str(base_dir), 'cdr_files', filename)
                    if os.path.exists(legacy_path):
                        cdr_file_full_path = legacy_path
        else:
            # If relative path provided, try MEDIA_ROOT first, then BASE_DIR
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            base_dir = getattr(settings, 'BASE_DIR', None)
            
            # Try MEDIA_ROOT location
            if media_root:
                media_path = os.path.join(str(media_root), cdr_file_path)
                if os.path.exists(media_path):
                    cdr_file_full_path = media_path
            
            # Try BASE_DIR location (legacy, for files in project root)
            if not cdr_file_full_path and base_dir:
                # Extract just the filename or path relative to cdr_files/
                if 'cdr_files/' in cdr_file_path:
                    filename = os.path.basename(cdr_file_path)
                    legacy_path = os.path.join(str(base_dir), 'cdr_files', filename)
                else:
                    legacy_path = os.path.join(str(base_dir), cdr_file_path)
                
                if os.path.exists(legacy_path):
                    cdr_file_full_path = legacy_path
        
        if not cdr_file_full_path or not os.path.exists(cdr_file_full_path):
            print(f"Error: CDR file not found")
            print(f"  Searched path: {cdr_file_path}")
            # List all attempted paths for debugging
            attempted_paths = []
            if os.path.isabs(cdr_file_path):
                attempted_paths.append(cdr_file_path)
            
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            base_dir = getattr(settings, 'BASE_DIR', None)
            
            if media_root and not os.path.isabs(cdr_file_path):
                attempted_paths.append(os.path.join(str(media_root), cdr_file_path))
            if base_dir:
                filename = os.path.basename(cdr_file_path)
                attempted_paths.append(os.path.join(str(base_dir), 'cdr_files', filename))
            
            for path in attempted_paths:
                print(f"  Tried: {path}")
            return
        
        # CloudConvert API base URL
        api_base = "https://api.cloudconvert.com/v2"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Step 1: Create a job with import, convert, and export tasks
        job_data = {
            "tasks": {
                "import-cdr": {
                    "operation": "import/upload"
                },
                "convert-to-pdf": {
                    "operation": "convert",
                    "input": "import-cdr",
                    "output_format": "pdf",
                    "input_format": "cdr"
                },
                "export-pdf": {
                    "operation": "export/url",
                    "input": "convert-to-pdf"
                }
            }
        }
        
        # Create the job
        response = requests.post(f"{api_base}/jobs", json=job_data, headers=headers)
        response.raise_for_status()
        job = response.json()
        job_id = job['data']['id']
        
        # Step 2: Find upload task and upload the CDR file
        upload_task = None
        for task in job['data']['tasks']:
            if task['operation'] == 'import/upload' and task['status'] == 'waiting':
                upload_task = task
                break
        
        if not upload_task:
            raise ValueError("Upload task not found in job")
        
        upload_url = upload_task['result']['form']['url']
        upload_form_data = upload_task['result']['form']['parameters']
        
        # Upload the CDR file
        with open(cdr_file_full_path, 'rb') as cdr_file:
            files = {'file': (os.path.basename(cdr_file_path), cdr_file)}
            upload_response = requests.post(upload_url, data=upload_form_data, files=files)
            upload_response.raise_for_status()
        
        # Step 3: Poll for job completion
        export_task_id = None
        for task in job['data']['tasks']:
            if task['operation'] == 'export/url':
                export_task_id = task['id']
                break
        
        if not export_task_id:
            raise ValueError("Export task not found in job")
        
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while True:
            status_response = requests.get(f"{api_base}/jobs/{job_id}", headers=headers)
            status_response.raise_for_status()
            job_status = status_response.json()['data']
            
            if job_status['status'] == 'finished':
                break
            elif job_status['status'] == 'error':
                error_msg = job_status.get('message', 'Unknown error')
                raise Exception(f"CloudConvert job failed: {error_msg}")
            
            if time.time() - start_time > max_wait_time:
                raise TimeoutError("CloudConvert conversion timeout (exceeded 5 minutes)")
            
            time.sleep(2)  # Wait 2 seconds before polling again
        
        # Step 4: Find and download the converted PDF
        export_task = None
        for task in job_status['tasks']:
            if task['id'] == export_task_id and task['status'] == 'finished':
                export_task = task
                break
        
        if not export_task or 'result' not in export_task or 'files' not in export_task['result']:
            raise ValueError("Export task not completed or no files found")
        
        pdf_url = export_task['result']['files'][0]['url']
        pdf_response = requests.get(pdf_url)
        pdf_response.raise_for_status()
        
        # Step 5: Save PDF to Django storage and update Caja instance
        pdf_filename = os.path.splitext(os.path.basename(cdr_file_path))[0] + '.pdf'
        pdf_file = ContentFile(pdf_response.content, name=pdf_filename)
        
        # Update the Caja instance
        caja = Caja.objects.get(pk=caja_id)
        caja.archivo_pdf.save(f'pdf_files/{pdf_filename}', pdf_file, save=True)
        
        print(f"Successfully converted CDR to PDF for Caja {caja_id}: {pdf_filename}")
        
    except Exception as e:
        # Log error (in production, use proper logging)
        print(f"Error converting CDR to PDF for Caja {caja_id}: {str(e)}")
        import traceback
        traceback.print_exc()

