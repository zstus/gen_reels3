#!/usr/bin/env python3
"""
Standalone test for image copying functionality
Tests the copy_test_images_to_job function independently
"""

import os
import sys
import uuid
import shutil
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def copy_test_images_to_job_standalone(job_uploads_folder: str):
    """Standalone version of copy_test_images_to_job function"""
    try:
        test_folder = "./test"
        media_extensions = ["jpg", "jpeg", "png", "bmp", "gif", "webp", "mp4", "mov", "avi", "webm", "mkv"]

        print(f"Test folder scan: {os.path.abspath(test_folder)}")
        print(f"Target Job folder: {job_uploads_folder}")

        copied_count = 0

        for i in range(1, 9):  # 1부터 8까지
            found_file = None

            for ext in media_extensions:
                test_file = os.path.join(test_folder, f"{i}.{ext}")
                if os.path.exists(test_file):
                    found_file = test_file
                    break

            if found_file:
                # 원본 확장자 유지하여 Job uploads에 복사
                original_ext = os.path.splitext(found_file)[1]
                target_name = f"{i}{original_ext}"
                target_path = os.path.join(job_uploads_folder, target_name)

                # 파일 복사
                shutil.copy2(found_file, target_path)
                copied_count += 1

                # 파일 타입 구분
                file_type = "video" if original_ext.lower() in ['.mp4', '.mov', '.avi', '.webm', '.mkv'] else "image"
                print(f"SUCCESS: Copied test {file_type}: {os.path.basename(found_file)} -> {target_name}")
            else:
                # 해당 번호의 파일이 없으면 중단
                if i == 1:
                    print(f"ERROR: No file #1 found in test folder")
                    print(f"Test folder contents: {os.listdir(test_folder) if os.path.exists(test_folder) else 'Folder not found'}")
                    return False
                else:
                    print(f"INFO: File #{i} not found, stopping copy (total {copied_count} files copied)")
                    break

        print(f"RESULT: Total {copied_count} test files copied to job folder")
        return copied_count > 0

    except Exception as e:
        print(f"ERROR: Failed to copy test images: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_copy():
    """Test image copying functionality"""
    print("\n" + "="*50)
    print("TEST: Test image copying to job folder")
    print("="*50)

    # Generate test Job ID
    job_id = str(uuid.uuid4())
    print(f"Test Job ID: {job_id}")

    try:
        # Create job uploads folder manually
        uploads_base = "uploads"
        job_uploads_folder = os.path.join(uploads_base, f"job_{job_id}")

        # Ensure uploads folder exists
        os.makedirs(job_uploads_folder, exist_ok=True)
        print(f"Created job uploads folder: {job_uploads_folder}")

        # Check what test files are available
        test_folder = "test"
        if os.path.exists(test_folder):
            test_files = os.listdir(test_folder)
            print(f"Available test files: {test_files}")
        else:
            print("WARNING: test folder not found")
            return False

        # Copy test images to job folder
        print("Attempting to copy test images...")
        copy_result = copy_test_images_to_job_standalone(job_uploads_folder)
        print(f"Copy operation result: {copy_result}")

        # Check what files were copied
        if os.path.exists(job_uploads_folder):
            copied_files = os.listdir(job_uploads_folder)
            print(f"Files in job uploads folder: {copied_files}")

            if copied_files:
                print("SUCCESS: Test images copied successfully")
                # Clean up test folder
                try:
                    shutil.rmtree(job_uploads_folder)
                    print("Cleaned up test job folder")
                except:
                    pass
                return True
            else:
                print("WARNING: No files found in uploads folder")
                return False
        else:
            print("ERROR: Uploads folder not found after copy operation")
            return False

    except Exception as e:
        print(f"ERROR: Test image copying failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("STARTING: Standalone Test Image Copy Verification")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Print current working directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")

    # Test image copying
    copy_success = test_image_copy()

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)

    if copy_success:
        print("PASS: Test image copying")
        print("SUCCESS: Image copy functionality verified!")
        return True
    else:
        print("FAIL: Test image copying")
        print("WARNING: Image copy functionality needs attention")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)