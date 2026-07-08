#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for automatic build of UI-for-ytdlp to exe.

Usage:
    python build.py

Requirements:
    - Python 3.10+
    - Installed dependencies: pip install -r requirements.txt

Result:
    dist/UI-for-ytdlp/UI-for-ytdlp.exe
"""

import subprocess
import shutil
import os
import sys

APP_NAME = 'UI-for-ytdlp'
DIST_APP_DIR = os.path.join('dist', APP_NAME)
EXE_PATH = os.path.join(DIST_APP_DIR, f'{APP_NAME}.exe')


def clean_build_dirs():
    """Clean build directories."""
    dirs_to_clean = ['build', 'dist']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/...")
            shutil.rmtree(dir_name)


def scaffold_dist_layout(app_dir: str) -> None:
    """Create utilities/ beside the onedir exe (matches runtime layout)."""
    utilities = os.path.join(app_dir, 'utilities')
    os.makedirs(utilities, exist_ok=True)

    gitkeep_src = os.path.join('utilities', '.gitkeep')
    gitkeep_dst = os.path.join(utilities, '.gitkeep')
    if os.path.exists(gitkeep_src):
        shutil.copy2(gitkeep_src, gitkeep_dst)
    elif not os.path.exists(gitkeep_dst):
        with open(gitkeep_dst, 'a', encoding='utf-8'):
            pass


def build_with_pyinstaller():
    """Build with PyInstaller."""
    print("\n=== Building UI-for-ytdlp ===\n")
    
    # Check spec file
    if not os.path.exists('UI-for-ytdlp.spec'):
        print("Error: UI-for-ytdlp.spec not found!")
        sys.exit(1)
    
    # Check icon
    if not os.path.exists('icon.ico'):
        print("Warning: icon.ico not found, building without icon")
    
    # Run PyInstaller
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'UI-for-ytdlp.spec'
    ]
    
    print(f"Running: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 50)
            print("BUILD SUCCESSFUL!")
            print("=" * 50)
            
            if os.path.exists(EXE_PATH):
                scaffold_dist_layout(DIST_APP_DIR)
                exe_size = os.path.getsize(EXE_PATH) / 1024 / 1024
                print(f"\nDirectory: {DIST_APP_DIR}")
                print(f"Executable: {EXE_PATH}")
                print(f"Exe size: {exe_size:.1f} MB")
            else:
                print(f"\nWarning: executable not found at {EXE_PATH}")
        else:
            print("\nBuild error!")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\nPyInstaller error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: PyInstaller not found!")
        print("Install: pip install pyinstaller")
        sys.exit(1)


def main():
    """Main function."""
    print("UI-for-ytdlp - Build Script")
    print("=" * 50)
    
    # Clean
    clean_build_dirs()
    
    # Build
    build_with_pyinstaller()
    
    print("\nDone!")


if __name__ == '__main__':
    main()
