"""File analysis and metadata extraction module."""

import hashlib
import logging
import os
import re
import stat
import subprocess
import tarfile
import zipfile
from typing import Any, Dict, Optional

import magic

try:
    import pefile
    PEFILE_AVAILABLE = True
except ImportError:
    PEFILE_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

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

        # Add file hashes (MD5, SHA1, SHA256)
        hashes = self._calculate_hashes(file_path)
        if hashes:
            file_info["hashes"] = hashes

        # Check if file is an archive and extract contents list
        archive_contents = self._get_archive_contents(file_path)
        if archive_contents:
            file_info["archive_contents"] = archive_contents

        # Extract executable metadata for Windows PE files
        if file_info["is_executable"]:
            exe_metadata = self._get_executable_metadata(file_path)
            if exe_metadata:
                file_info["executable_metadata"] = exe_metadata

        # Extract PDF metadata and content
        if file_info["file_type"] == ".pdf":
            pdf_metadata = self._get_pdf_metadata(file_path)
            if pdf_metadata:
                file_info["pdf_metadata"] = pdf_metadata
            pdf_content = self._get_pdf_content(file_path)
            if pdf_content:
                file_info["pdf_content"] = pdf_content

        # Extract text content for text files
        if file_info["file_type"] == ".txt" or file_info["mime_type"] == "text/plain":
            text_content = self._get_text_content(file_path)
            if text_content:
                file_info["text_content"] = text_content

        # Extract image metadata
        if file_info["mime_type"] and file_info["mime_type"].startswith("image/"):
            image_metadata = self._get_image_metadata(file_path)
            if image_metadata:
                file_info["image_metadata"] = image_metadata

        # Extract video metadata
        if file_info["mime_type"] and file_info["mime_type"].startswith("video/"):
            video_metadata = self._get_video_metadata(file_path)
            if video_metadata:
                file_info["video_metadata"] = video_metadata

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

    def _get_executable_metadata(self, file_path: str) -> Optional[Dict[str, str]]:
        """
        Extract metadata from Windows PE executables (EXE, DLL).

        Args:
            file_path: Path to the executable file

        Returns:
            Dictionary containing executable metadata or None if not a PE file
        """
        if not PEFILE_AVAILABLE:
            logger.debug("pefile library not available, skipping executable metadata extraction")
            return None

        try:
            pe = pefile.PE(file_path, fast_load=True)
            try:
                pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])

                metadata = {}

                # Extract version information if available
                if hasattr(pe, 'FileInfo') and pe.FileInfo:
                    for fileinfo in pe.FileInfo:
                        if fileinfo.Key == b'StringFileInfo':
                            for st in fileinfo.StringTable:
                                for entry in st.entries.items():
                                    key = entry[0].decode('utf-8', errors='ignore')
                                    value = entry[1].decode('utf-8', errors='ignore')
                                    # Common version info fields
                                    if key in ['FileDescription', 'ProductName', 'CompanyName', 
                                              'FileVersion', 'ProductVersion', 'LegalCopyright',
                                              'OriginalFilename', 'InternalName']:
                                        metadata[key] = value

                return metadata if metadata else None
            finally:
                pe.close()

        except (pefile.PEFormatError, OSError, IOError) as e:
            logger.debug(f"Failed to parse PE file {file_path}: {str(e)}")
            return None

    def _calculate_hashes(self, file_path: str) -> Optional[Dict[str, str]]:
        """
        Calculate MD5, SHA1, and SHA256 hashes for a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing hash values or None if calculation failed
        """
        try:
            md5_hash = hashlib.md5()
            sha1_hash = hashlib.sha1()
            sha256_hash = hashlib.sha256()

            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
                    sha1_hash.update(chunk)
                    sha256_hash.update(chunk)

            return {
                "md5": md5_hash.hexdigest(),
                "sha1": sha1_hash.hexdigest(),
                "sha256": sha256_hash.hexdigest(),
            }
        except (IOError, OSError) as e:
            logger.warning(f"Failed to calculate hashes for {file_path}: {str(e)}")
            return None

    def _get_pdf_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from PDF files.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing PDF metadata or None if extraction failed
        """
        if not PYPDF2_AVAILABLE:
            logger.debug("pypdf library not available, skipping PDF metadata extraction")
            return None

        try:
            with open(file_path, "rb") as f:
                pdf_reader = PdfReader(f)
                metadata = {}

                # Extract document information
                if pdf_reader.metadata:
                    for key, value in pdf_reader.metadata.items():
                        # Remove the '/' prefix from keys
                        clean_key = key[1:] if key.startswith('/') else key
                        metadata[clean_key] = str(value)

                # Add page count
                metadata["page_count"] = len(pdf_reader.pages)

                return metadata if metadata else None
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata from {file_path}: {str(e)}")
            return None

    def _get_pdf_content(self, file_path: str, max_sentences: int = 3) -> Optional[str]:
        """
        Extract first few sentences from a PDF file.

        Args:
            file_path: Path to the PDF file
            max_sentences: Maximum number of sentences to extract (default: 3)

        Returns:
            String containing the first few sentences or None if extraction failed
        """
        if not PYPDF2_AVAILABLE:
            logger.debug("pypdf library not available, skipping PDF content extraction")
            return None

        try:
            with open(file_path, "rb") as f:
                pdf_reader = PdfReader(f)
                
                # Extract text from first few pages
                text = ""
                for page_num in range(min(3, len(pdf_reader.pages))):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
                
                # Get first few sentences
                if text:
                    # Simple sentence splitting (split by '. ', '! ', '? ')
                    sentences = re.split(r'[.!?]\s+', text.strip())
                    sentences = [s.strip() for s in sentences if s.strip()]
                    return ' '.join(sentences[:max_sentences])
                
                return None
        except Exception as e:
            logger.warning(f"Failed to extract PDF content from {file_path}: {str(e)}")
            return None

    def _get_text_content(self, file_path: str, max_sentences: int = 3) -> Optional[str]:
        """
        Extract first few sentences from a text file.

        Args:
            file_path: Path to the text file
            max_sentences: Maximum number of sentences to extract (default: 3)

        Returns:
            String containing the first few sentences or None if extraction failed
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(2000)  # Read first 2000 characters
                
                if text:
                    # Simple sentence splitting
                    sentences = re.split(r'[.!?]\s+', text.strip())
                    sentences = [s.strip() for s in sentences if s.strip()]
                    return ' '.join(sentences[:max_sentences])
                
                return None
        except Exception as e:
            logger.warning(f"Failed to extract text content from {file_path}: {str(e)}")
            return None

    def _get_image_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from image files (EXIF data).

        Args:
            file_path: Path to the image file

        Returns:
            Dictionary containing image metadata or None if extraction failed
        """
        if not PILLOW_AVAILABLE:
            logger.debug("Pillow library not available, skipping image metadata extraction")
            return None

        try:
            image = Image.open(file_path)
            metadata = {}

            # Basic image information
            metadata["format"] = image.format
            metadata["mode"] = image.mode
            metadata["size"] = {"width": image.width, "height": image.height}

            # Extract EXIF data
            exif_data = image.getexif()
            if exif_data:
                exif_metadata = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    # Convert to string if not already
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except (UnicodeDecodeError, AttributeError):
                            value = str(value)
                    
                    # Handle special tags
                    if tag == "GPSInfo":
                        gps_data = {}
                        for gps_tag_id in value:
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = str(value[gps_tag_id])
                        exif_metadata["GPSInfo"] = gps_data
                    else:
                        exif_metadata[str(tag)] = str(value)
                
                if exif_metadata:
                    metadata["exif"] = exif_metadata

            return metadata if len(metadata) > 3 else None  # Return only if we have more than basic info
        except Exception as e:
            logger.warning(f"Failed to extract image metadata from {file_path}: {str(e)}")
            return None

    def _get_video_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from video files using ffmpeg.

        Args:
            file_path: Path to the video file

        Returns:
            Dictionary containing video metadata or None if extraction failed
        """
        if not FFMPEG_AVAILABLE:
            logger.debug("ffmpeg-python library not available, skipping video metadata extraction")
            return None

        try:
            # Use ffmpeg-python library to probe video file
            probe = ffmpeg.probe(file_path)
            
            metadata = {}
            
            # Extract format information
            if "format" in probe:
                format_info = probe["format"]
                if "duration" in format_info:
                    metadata["duration"] = float(format_info["duration"])
                if "size" in format_info:
                    metadata["size"] = int(format_info["size"])
                if "bit_rate" in format_info:
                    metadata["bit_rate"] = int(format_info["bit_rate"])
                if "format_name" in format_info:
                    metadata["format"] = format_info["format_name"]
            
            # Extract video stream information
            video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
            if video_streams:
                video = video_streams[0]
                metadata["video"] = {}
                if "codec_name" in video:
                    metadata["video"]["codec"] = video["codec_name"]
                if "width" in video:
                    metadata["video"]["width"] = video["width"]
                if "height" in video:
                    metadata["video"]["height"] = video["height"]
                if "width" in video and "height" in video:
                    metadata["video"]["resolution"] = f"{video['width']}x{video['height']}"
                if "avg_frame_rate" in video:
                    metadata["video"]["frame_rate"] = video["avg_frame_rate"]
            
            # Extract audio stream information
            audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
            if audio_streams:
                audio = audio_streams[0]
                metadata["audio"] = {}
                if "codec_name" in audio:
                    metadata["audio"]["codec"] = audio["codec_name"]
                if "sample_rate" in audio:
                    metadata["audio"]["sample_rate"] = audio["sample_rate"]
                if "channels" in audio:
                    metadata["audio"]["channels"] = audio["channels"]

            return metadata if metadata else None
        except Exception as e:
            logger.warning(f"Failed to extract video metadata from {file_path}: {str(e)}")
            # Try using subprocess as fallback if ffprobe is available
            # Note: ffmpeg-python library already validates file paths
            try:
                # Validate file_path to prevent command injection
                if not os.path.isfile(file_path):
                    logger.warning(f"File does not exist: {file_path}")
                    return None
                
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height",
                     "-of", "default=noprint_wrappers=1", file_path],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=False  # Explicitly disable shell to prevent command injection
                )
                if result.returncode == 0 and result.stdout:
                    # Parse basic info from ffprobe output
                    metadata = {}
                    for line in result.stdout.split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            metadata[key] = value
                    return metadata if metadata else None
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                logger.debug(f"ffprobe command also failed: {str(e)}")
            
            return None


