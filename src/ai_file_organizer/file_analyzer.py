"""File analysis and metadata extraction module."""

import logging
import os
import stat
import tarfile
import zipfile
from typing import Any, Dict, Optional

import magic

logger = logging.getLogger(__name__)


class FileAnalyzer:
    """Analyze files and extract metadata."""

    def __init__(self):
        """Initialize the file analyzer."""
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.warning(
                f"Failed to initialize python-magic: {e}. MIME type detection will be limited."
            )
            self.magic = None

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a file and extract metadata.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dictionary containing file information
        """
        file_info = {
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_type": self._get_file_extension(file_path),
            "mime_type": self._get_mime_type(file_path),
            "is_executable": self._is_executable(file_path),
        }

        # Check if file is an archive and extract contents list
        archive_contents = self._get_archive_contents(file_path)
        if archive_contents:
            file_info["archive_contents"] = archive_contents

        # Add file stats as metadata
        file_stats = os.stat(file_path)
        file_info["metadata"] = {
            "created": file_stats.st_ctime,
            "modified": file_stats.st_mtime,
            "accessed": file_stats.st_atime,
            "mode": oct(file_stats.st_mode),
        }

        return file_info

    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension."""
        _, ext = os.path.splitext(file_path)
        return ext.lower() if ext else "no_extension"

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type of the file."""
        if self.magic is None:
            # Fallback to basic extension-based detection
            ext = self._get_file_extension(file_path).lower()
            mime_map = {
                ".txt": "text/plain",
                ".pdf": "application/pdf",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".zip": "application/zip",
                ".tar": "application/x-tar",
                ".gz": "application/gzip",
                ".doc": "application/msword",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".xls": "application/vnd.ms-excel",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            return mime_map.get(ext, "application/octet-stream")

        try:
            return self.magic.from_file(file_path)
        except (IOError, OSError):
            return "unknown"

    def _is_executable(self, file_path: str) -> bool:
        """Check if file is executable (detects Unix, Windows, shebang, and binary magic numbers on any platform)."""
        try:
            # Check for Windows executable extensions
            executable_exts = {".exe", ".bat", ".cmd", ".com", ".ps1"}
            _, ext = os.path.splitext(file_path)
            if ext.lower() in executable_exts:
                return True

            # Check for shebang (#!) at the start of the file and binary magic numbers
            try:
                with open(file_path, "rb") as f:
                    first_bytes = f.read(4)
                    # Shebang
                    if first_bytes[:2] == b"#!":
                        return True
                    # ELF (Linux)
                    if first_bytes == b"\x7fELF":
                        return True
                    # PE (Windows EXE/DLL)
                    if first_bytes[:2] == b"MZ":
                        return True
                    # Mach-O (macOS)
                    if first_bytes in [
                        b"\xfe\xed\xfa\xce",
                        b"\xfe\xed\xfa\xcf",
                        b"\xca\xfe\xba\xbe",
                        b"\xcf\xfa\xed\xfe",
                    ]:
                        return True
            except Exception:
                pass

            # Check Unix executable bit
            file_stats = os.stat(file_path)
            return bool(file_stats.st_mode & stat.S_IXUSR)
        except Exception:
            return False

    def _get_archive_contents(self, file_path: str) -> Optional[str]:
        """
        Get list of files in an archive.

        Args:
            file_path: Path to the archive file

        Returns:
            String listing archive contents or None if not an archive
        """
        try:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, "r") as zf:
                    files = zf.namelist()
                    return "\n".join(files[:50])  # Limit to first 50 files
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, "r") as tf:
                    files = tf.getnames()
                    return "\n".join(files[:50])  # Limit to first 50 files
        except (IOError, OSError, zipfile.BadZipFile, tarfile.TarError) as e:
            logger.warning(f"Failed to read archive contents for {file_path}: {str(e)}")

        return None
