#!/usr/bin/env python3
"""
Simple Folder Manager Test (no Unicode)
Job ID-based folder isolation and monthly output structure verification
"""

import os
import sys
import uuid
import shutil
from datetime import datetime

# Add current directory to path for folder_manager import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from folder_manager import FolderManager, create_job_folders, get_job_folders, cleanup_job_folders
    print("SUCCESS: folder_manager module imported")
except ImportError as e:
    print(f"ERROR: folder_manager import failed: {e}")
    sys.exit(1)

def test_folder_creation():
    """Test Job folder creation"""
    print("\n" + "="*50)
    print("TEST: Job folder creation")
    print("="*50)

    # Generate test Job ID
    job_id = str(uuid.uuid4())
    print(f"Test Job ID: {job_id}")

    try:
        # Create Job folders
        uploads_folder, output_folder = create_job_folders(job_id)

        print(f"uploads folder: {uploads_folder}")
        print(f"output folder: {output_folder}")

        # Check folder existence
        uploads_exists = os.path.exists(uploads_folder)
        output_exists = os.path.exists(output_folder)

        print(f"uploads folder exists: {uploads_exists}")
        print(f"output folder exists: {output_exists}")

        # Verify folder structure
        expected_uploads = f"uploads{os.sep}job_{job_id}"
        current_month = datetime.now().strftime("%Y%m")
        expected_output = f"output_videos{os.sep}{current_month}"

        print(f"Expected uploads path: {expected_uploads}")
        print(f"Expected output path: {expected_output}")

        uploads_correct = uploads_folder.endswith(expected_uploads)
        output_correct = output_folder.endswith(expected_output)

        print(f"uploads path correct: {uploads_correct}")
        print(f"output path correct (monthly): {output_correct}")

        if uploads_exists and output_exists and uploads_correct and output_correct:
            print("SUCCESS: Job folder creation test passed!")
            return job_id, uploads_folder, output_folder
        else:
            print("FAIL: Job folder creation test failed")
            return None, None, None

    except Exception as e:
        print(f"ERROR: Job folder creation failed: {e}")
        return None, None, None

def test_file_isolation():
    """Test file isolation"""
    print("\n" + "="*50)
    print("TEST: File isolation")
    print("="*50)

    # Generate two different Job IDs
    job_id_1 = str(uuid.uuid4())
    job_id_2 = str(uuid.uuid4())

    print(f"Job 1 ID: {job_id_1}")
    print(f"Job 2 ID: {job_id_2}")

    try:
        # Create two Job folders
        uploads_1, output_1 = create_job_folders(job_id_1)
        uploads_2, output_2 = create_job_folders(job_id_2)

        print(f"Job 1 uploads: {uploads_1}")
        print(f"Job 2 uploads: {uploads_2}")
        print(f"Job 1 output: {output_1}")
        print(f"Job 2 output: {output_2}")

        # Create test files in each Job folder
        test_file_1 = os.path.join(uploads_1, "test_file_1.txt")
        test_file_2 = os.path.join(uploads_2, "test_file_2.txt")

        with open(test_file_1, 'w', encoding='utf-8') as f:
            f.write(f"Job 1 test file - {job_id_1}")

        with open(test_file_2, 'w', encoding='utf-8') as f:
            f.write(f"Job 2 test file - {job_id_2}")

        print(f"Job 1 test file created: {test_file_1}")
        print(f"Job 2 test file created: {test_file_2}")

        # Verify file isolation
        file_1_exists = os.path.exists(test_file_1)
        file_2_exists = os.path.exists(test_file_2)
        uploads_isolated = uploads_1 != uploads_2

        print(f"Job 1 file exists: {file_1_exists}")
        print(f"Job 2 file exists: {file_2_exists}")
        print(f"uploads folders isolated: {uploads_isolated}")

        # Verify output folders are shared monthly
        output_shared = output_1 == output_2
        print(f"output folders shared (monthly): {output_shared}")

        if file_1_exists and file_2_exists and uploads_isolated and output_shared:
            print("SUCCESS: File isolation test passed!")
            return True
        else:
            print("FAIL: File isolation test failed")
            return False

    except Exception as e:
        print(f"ERROR: File isolation test failed: {e}")
        return False

def test_cleanup():
    """Test folder cleanup"""
    print("\n" + "="*50)
    print("TEST: Folder cleanup")
    print("="*50)

    # Generate test Job ID
    job_id = str(uuid.uuid4())
    print(f"Test Job ID: {job_id}")

    try:
        # Create Job folders
        uploads_folder, output_folder = create_job_folders(job_id)

        # Create test file
        test_file = os.path.join(uploads_folder, "test_cleanup.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Cleanup test file")

        print(f"Test file created: {test_file}")

        # Check existence before cleanup
        file_exists_before = os.path.exists(test_file)
        uploads_exists_before = os.path.exists(uploads_folder)

        print(f"Before cleanup - file exists: {file_exists_before}")
        print(f"Before cleanup - uploads folder exists: {uploads_exists_before}")

        # Execute cleanup
        cleanup_success = cleanup_job_folders(job_id, keep_output=True)

        # Check state after cleanup
        file_exists_after = os.path.exists(test_file)
        uploads_exists_after = os.path.exists(uploads_folder)
        output_exists_after = os.path.exists(output_folder)

        print(f"After cleanup - file exists: {file_exists_after}")
        print(f"After cleanup - uploads folder exists: {uploads_exists_after}")
        print(f"After cleanup - output folder exists: {output_exists_after}")
        print(f"Cleanup operation success: {cleanup_success}")

        # Expected result: uploads deleted, output preserved
        expected_result = (not file_exists_after and
                         not uploads_exists_after and
                         output_exists_after and
                         cleanup_success)

        if expected_result:
            print("SUCCESS: Folder cleanup test passed!")
            return True
        else:
            print("FAIL: Folder cleanup test failed")
            return False

    except Exception as e:
        print(f"ERROR: Folder cleanup test failed: {e}")
        return False

def main():
    """Main test function"""
    print("STARTING: Folder Manager Independent Test")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Print current working directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")

    test_results = []

    # 1. Folder creation test
    job_id, uploads_folder, output_folder = test_folder_creation()
    test_results.append(("Folder creation", job_id is not None))

    # 2. File isolation test
    isolation_success = test_file_isolation()
    test_results.append(("File isolation", isolation_success))

    # 3. Folder cleanup test
    cleanup_success = test_cleanup()
    test_results.append(("Folder cleanup", cleanup_success))

    # Results summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)

    total_tests = len(test_results)
    passed_tests = sum(1 for _, result in test_results if result)

    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")

    print("="*60)
    print(f"Overall result: {passed_tests}/{total_tests} passed")

    if passed_tests == total_tests:
        print("SUCCESS: All tests passed! Concurrency issue resolved!")
        return True
    else:
        print("WARNING: Some tests failed. Additional fixes needed")
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