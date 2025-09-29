#!/usr/bin/env python3
"""
Test image copying functionality
Verify that test images are properly copied to job folders
"""

import os
import sys
import uuid
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from folder_manager import create_job_folders
    from main import copy_test_images_to_job
    print("SUCCESS: Required modules imported")
except ImportError as e:
    print(f"ERROR: Module import failed: {e}")
    sys.exit(1)

def test_copy_images():
    """Test copying test images to job folder"""
    print("\n" + "="*50)
    print("TEST: Test image copying")
    print("="*50)

    # Generate test Job ID
    job_id = str(uuid.uuid4())
    print(f"Test Job ID: {job_id}")

    try:
        # Create job folders
        uploads_folder, output_folder = create_job_folders(job_id)
        print(f"Created uploads folder: {uploads_folder}")
        print(f"Created output folder: {output_folder}")

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
        copy_result = copy_test_images_to_job(job_id)
        print(f"Copy operation result: {copy_result}")

        # Check what files were copied
        if os.path.exists(uploads_folder):
            copied_files = os.listdir(uploads_folder)
            print(f"Files in job uploads folder: {copied_files}")

            if copied_files:
                print("SUCCESS: Test images copied successfully")
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
    print("STARTING: Test Image Copy Verification")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Print current working directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")

    # Test image copying
    copy_success = test_copy_images()

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