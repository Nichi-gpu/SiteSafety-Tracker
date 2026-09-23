import os
import zipfile

OUTPUT_ZIP = "CPE100L_A6_Group1_SiteSafetyTracker_ProgressReport_Sept23.zip"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Files and directories to exclude from the academic submission zip
EXCLUDE_DIRS = {'.git', '__pycache__', '.tempmediaStorage', '.user_uploaded', 'scratch'}
EXCLUDE_FILES = {
    OUTPUT_ZIP,
    '.gitignore',
    'scratch',
    'package_submission.py'
}

def create_submission_zip():
    print(f"Creating submission zip: {OUTPUT_ZIP}...")
    file_count = 0
    with zipfile.ZipFile(os.path.join(ROOT_DIR, OUTPUT_ZIP), 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
            
            for file in files:
                if file in EXCLUDE_FILES or file.endswith('.pyc') or file.startswith('.'):
                    continue
                
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ROOT_DIR)
                zipf.write(full_path, rel_path)
                file_count += 1
                print(f"  + Added: {rel_path}")

    print(f"\n[OK] Successfully packaged {file_count} files into '{OUTPUT_ZIP}'!")

if __name__ == '__main__':
    create_submission_zip()
