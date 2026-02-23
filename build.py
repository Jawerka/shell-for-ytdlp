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
    dist/UI-for-ytdlp.exe
"""

import subprocess
import shutil
import os
import sys


def clean_build_dirs():
    """Clean build directories."""
    dirs_to_clean = ['build', 'dist']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/...")
            shutil.rmtree(dir_name)


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
            
            # Check exe
            exe_path = os.path.join('dist', 'UI-for-ytdlp.exe')
            if os.path.exists(exe_path):
                exe_size = os.path.getsize(exe_path) / 1024 / 1024
                print(f"\nFile: {exe_path}")
                print(f"Size: {exe_size:.1f} MB")
            else:
                print("\nWarning: exe file not found in dist/")
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
    print("Shell for yt-dlp - Build Script")
    print("=" * 50)
    
    # Clean
    clean_build_dirs()
    
    # Build
    build_with_pyinstaller()
    
    print("\nDone!")


if __name__ == '__main__':
    main()
