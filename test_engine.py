import os
import csv
import pytest
from unittest.mock import Mock, patch
from engine import Finder, PdfEntry, CallBack, CALLBACK_FILE_VALIDATED, CALLBACK_FILE_COPIED

# Test fixtures
@pytest.fixture
def sample_pdf_content():
    """Return a minimal valid PDF content for testing."""
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory structure for testing."""
    # Create test structure:
    # temp_dir/
    # ├── pdf1.pdf
    #   ├── subfolder/
    #       ├── pdf2.pdf
    return tmp_path


@pytest.fixture
def create_sample_pdfs(temp_dir, sample_pdf_content):
    """Create sample PDF files in the temp directory."""
    # Root level PDF
    pdf1 = temp_dir / "pdf1.pdf"
    pdf1.write_bytes(sample_pdf_content)
    
    # Subfolder PDF
    subfolder = temp_dir / "subfolder"
    subfolder.mkdir()
    pdf2 = subfolder / "pdf2.pdf"
    pdf2.write_bytes(sample_pdf_content)
    
    return pdf1, pdf2


@pytest.fixture
def finder():
    """Create a Finder instance."""
    return Finder()


class TestPdfEntry:
    """Tests for PdfEntry dataclass."""
    
    def test_create_pdf_entry(self):
        """Test creating a PdfEntry with all fields."""
        entry = PdfEntry(
            fullname="/path/to/file.pdf",
            size=1024,
            hash="abc123",
            pages=10,
            info={"title": "Test"},
            is_duplicate=False
        )
        assert entry.fullname == "/path/to/file.pdf"
        assert entry.size == 1024
        assert entry.hash == "abc123"
        assert entry.pages == 10
        assert entry.info == {"title": "Test"}
        assert entry.is_duplicate is False
    
    def test_create_pdf_entry_defaults(self):
        """Test creating a PdfEntry with default values."""
        entry = PdfEntry(fullname="/path/to/file.pdf", size=500, hash="")
        assert entry.pages is None
        assert entry.info is None
        assert entry.is_duplicate is False
    
    def test_to_dict(self):
        """Test converting PdfEntry to dictionary."""
        entry = PdfEntry(
            fullname="/path/to/file.pdf",
            size=1024,
            hash="abc123",
            pages=5,
            info={"title": "Test Doc", "author": "Test Author"},
            is_duplicate=True
        )
        
        result = entry.to_dict()
        assert result["fullname"] == "/path/to/file.pdf"
        assert result["size"] == 1024
        assert result["hash"] == "abc123"
        assert result["pages"] == 5
        assert result["is_duplicate"] is True
        assert result["title"] == "Test Doc"
        assert result["author"] == "Test Author"
        assert "MB" in result["size_human"] or "KB" in result["size_human"]
    
    def test_to_dict_empty_pages(self):
        """Test to_dict when pages is None."""
        entry = PdfEntry(fullname="/path/to/file.pdf", size=100, hash="")
        result = entry.to_dict()
        assert result["pages"] == ""
    
    def test_to_dict_empty_info(self):
        """Test to_dict when info is None."""
        entry = PdfEntry(fullname="/path/to/file.pdf", size=100, hash="")
        result = entry.to_dict()
        assert result["title"] == ""
        assert result["author"] == ""


class TestFinderFindAllPdfFiles:
    """Tests for Finder.find_all_pdf_files method."""
    
    def test_find_pdfs_in_empty_dir(self, temp_dir, finder):
        """Test finding PDFs in an empty directory."""
        result = finder.find_all_pdf_files(str(temp_dir))
        assert result == []
    
    def test_find_single_pdf(self, temp_dir, sample_pdf_content, finder):
        """Test finding a single PDF file."""
        pdf = temp_dir / "test.pdf"
        pdf.write_bytes(sample_pdf_content)
        
        result = finder.find_all_pdf_files(str(temp_dir))
        assert len(result) == 1
        assert result[0].fullname == str(pdf)
        assert result[0].hash == ""
        assert result[0].pages is None
    
    def test_find_multiple_pdfs(self, create_sample_pdfs, finder):
        """Test finding multiple PDF files."""
        result = finder.find_all_pdf_files(str(create_sample_pdfs[0].parent))
        assert len(result) == 2
    
    def test_find_pdfs_recursively(self, create_sample_pdfs, finder):
        """Test finding PDFs in subdirectories."""
        result = finder.find_all_pdf_files(str(create_sample_pdfs[0].parent))
        fullnames = [entry.fullname for entry in result]
        assert any("pdf1.pdf" in name for name in fullnames)
        assert any("pdf2.pdf" in name for name in fullnames)
    
    def test_find_no_pdf_extension(self, temp_dir, finder):
        """Test that non-PDF files are ignored."""
        txt = temp_dir / "test.txt"
        txt.write_text("not a pdf")
        
        result = finder.find_all_pdf_files(str(temp_dir))
        assert result == []
    
    def test_find_calls_callback(self, temp_dir, sample_pdf_content, finder):
        """Test that callback is called when files are found."""
        pdf = temp_dir / "test.pdf"
        pdf.write_bytes(sample_pdf_content)
        
        mock_callback = Mock()
        mock_callback.is_cancelled.return_value = False
        finder.find_all_pdf_files(str(temp_dir), callback=mock_callback)
        
        # Should call callback at least once for the root folder
        assert mock_callback.update.called


class TestFinderValidatePdfs:
    """Tests for Finder.validate_pdfs method."""
    
    def test_validate_with_page_filter(self, finder):
        """Test filtering PDFs by minimum page count."""
        # Mock _read_pdf_info to avoid file I/O
        with patch.object(finder, '_read_pdf_info', return_value=None):
            entries = [
                PdfEntry(fullname="/test/test.pdf", size=100, hash="", pages=5),
                PdfEntry(fullname="/test/test2.pdf", size=100, hash="", pages=15)
            ]
            
            result = finder.validate_pdfs(entries, page_filter=10)
            assert len(result) == 1
            assert result[0].pages == 15  # min filter: keep pages >= 10
    
    def test_validate_with_size_filter(self, finder):
        """Test filtering PDFs by minimum file size."""
        # Mock _read_pdf_info to avoid file I/O
        with patch.object(finder, '_read_pdf_info', return_value=None):
            entries = [
                PdfEntry(fullname="/test/test.pdf", size=500, hash=""),
                PdfEntry(fullname="/test/test2.pdf", size=1500, hash="")
            ]
            
            result = finder.validate_pdfs(entries, size_filter=1000)
            assert len(result) == 1
            assert result[0].size == 1500  # min filter: keep size >= 1000
    
    def test_validate_no_filter(self, finder):
        """Test validation with no filters applied."""
        # Mock _read_pdf_info to avoid file I/O
        with patch.object(finder, '_read_pdf_info', return_value=None) as mock_read:
            entries = [
                PdfEntry(fullname="/test/test.pdf", size=100, hash="", pages=5)
            ]
            result = finder.validate_pdfs(entries)
            assert len(result) == 1
            mock_read.assert_called_once()
    
    def test_validate_minimum_page_filter(self, finder):
        """Test minimum page filter: files below threshold are excluded."""
        with patch.object(finder, '_read_pdf_info', return_value=None):
            entries = [
                PdfEntry(fullname="/test/test.pdf", size=100, hash="", pages=3),
                PdfEntry(fullname="/test/test2.pdf", size=100, hash="", pages=7),
                PdfEntry(fullname="/test/test3.pdf", size=100, hash="", pages=10)
            ]
            result = finder.validate_pdfs(entries, page_filter=5)
            assert len(result) == 2
            assert result[0].pages == 7
            assert result[1].pages == 10
    
    def test_validate_minimum_size_filter(self, finder):
        """Test minimum size filter: files below threshold are excluded."""
        with patch.object(finder, '_read_pdf_info', return_value=None):
            entries = [
                PdfEntry(fullname="/test/test.pdf", size=100, hash=""),
                PdfEntry(fullname="/test/test2.pdf", size=500, hash=""),
                PdfEntry(fullname="/test/test3.pdf", size=1000, hash="")
            ]
            result = finder.validate_pdfs(entries, size_filter=500)
            assert len(result) == 2
            assert result[0].size == 500
            assert result[1].size == 1000
    
    def test_validate_with_duplicate_detection(self, finder):
        """Test validation with duplicate detection enabled."""
        # Mock _read_pdf_info to avoid file I/O
        with patch.object(finder, '_read_pdf_info', return_value=None):
            with patch.object(finder, '_calculate_hash', return_value='abc123') as mock_hash:
                entries = [
                    PdfEntry(fullname="/test/test.pdf", size=100, hash="")
                ]
                result = finder.validate_pdfs(entries, detect_duplicates=True)
                assert len(result) == 1
                assert result[0].hash == "abc123"
                mock_hash.assert_called_once()
    
    def test_validate_cancellation(self, finder):
        """Test that validation stops when cancelled."""
        with patch.object(finder, '_read_pdf_info', return_value=None):
            entries = [
                PdfEntry(fullname="/test/test.pdf", size=100, hash="", pages=5),
                PdfEntry(fullname="/test/test2.pdf", size=200, hash="", pages=10),
                PdfEntry(fullname="/test/test3.pdf", size=300, hash="", pages=15),
            ]
            mock_callback = Mock()
            mock_callback.is_cancelled.return_value = False
            # Cancel on the second call
            call_count = [0]
            def should_cancel():
                call_count[0] += 1
                return call_count[0] >= 2
            mock_callback.is_cancelled.side_effect = should_cancel
            
            result = finder.validate_pdfs(entries, callback=mock_callback)
            # Should stop after processing 1 entry (the second check cancels)
            assert len(result) == 1
    
    def test_validate_invalid_pdf(self, temp_dir, finder):
        """Test validation of invalid PDF files."""
        invalid_pdf = temp_dir / "invalid.pdf"
        invalid_pdf.write_bytes(b"this is not a valid PDF")
        
        entries = [PdfEntry(fullname=str(invalid_pdf), size=invalid_pdf.stat().st_size, hash="")]
        result = finder.validate_pdfs(entries)
        
        # Invalid entries should remain in result with is_valid=False
        assert len(result) == 1
        assert result[0].is_valid is False
    
    def test_validate_calls_callback(self, finder):
        """Test that callback is called during validation."""
        # Mock _read_pdf_info to avoid file I/O
        with patch.object(finder, '_read_pdf_info', return_value=None):
            entries = [
                PdfEntry(fullname="/test/test.pdf", size=100, hash="")
            ]
            mock_callback = Mock()
            mock_callback.is_cancelled.return_value = False
            finder.validate_pdfs(entries, callback=mock_callback)
            assert mock_callback.update.called
    
    def test_validate_hash_calculation_failure(self, temp_dir, finder, sample_pdf_content):
        """Test validation when hash calculation fails."""
        pdf = temp_dir / "test.pdf"
        pdf.write_bytes(sample_pdf_content)
        
        entries = [PdfEntry(fullname=str(pdf), size=pdf.stat().st_size, hash="")]
        
        # Mock _read_pdf_info to avoid file I/O and _calculate_hash to raise exception
        with patch.object(finder, '_read_pdf_info', return_value=None):
            with patch.object(finder, '_calculate_hash', side_effect=Exception("Hash failed")):
                result = finder.validate_pdfs(entries, detect_duplicates=True)
        
        # Entry should still be included with hash="N/A"
        assert len(result) == 1
        assert result[0].hash == "N/A"
    
    def test_validate_callback_on_exception(self, temp_dir, finder):
        """Test that callback is called when validation fails."""
        invalid_pdf = temp_dir / "invalid.pdf"
        invalid_pdf.write_bytes(b"not a valid PDF")
        
        entries = [PdfEntry(fullname=str(invalid_pdf), size=invalid_pdf.stat().st_size, hash="")]
        mock_callback = Mock()
        mock_callback.is_cancelled.return_value = False
        
        finder.validate_pdfs(entries, callback=mock_callback)
        
        # Callback should be called with error message
        assert mock_callback.update.called
        call_args = mock_callback.update.call_args
        assert call_args[0][0] == CALLBACK_FILE_VALIDATED
        assert "Failed to validate" in call_args[0][1]


class TestFinderDetectDuplicates:
    """Tests for Finder.detect_duplicates method."""
    
    def test_no_duplicates(self, finder):
        """Test detection with no duplicates."""
        entries = [
            PdfEntry(fullname="/path/1.pdf", size=100, hash="hash1"),
            PdfEntry(fullname="/path/2.pdf", size=200, hash="hash2"),
            PdfEntry(fullname="/path/3.pdf", size=300, hash="hash3")
        ]
        
        result = finder.detect_duplicates(entries)
        assert all(not entry.is_duplicate for entry in result)
    
    def test_with_duplicates(self, finder):
        """Test detection with duplicates."""
        entries = [
            PdfEntry(fullname="/path/1.pdf", size=100, hash="hash1"),
            PdfEntry(fullname="/path/2.pdf", size=200, hash="hash2"),
            PdfEntry(fullname="/path/3.pdf", size=100, hash="hash1")  # Duplicate
        ]
        
        result = finder.detect_duplicates(entries)
        
        assert result[0].is_duplicate is False  # First occurrence
        assert result[1].is_duplicate is False
        assert result[2].is_duplicate is True   # Duplicate marked
    
    def test_ignore_na_hash(self, finder):
        """Test that N/A hashes are not considered duplicates."""
        entries = [
            PdfEntry(fullname="/path/1.pdf", size=100, hash="N/A"),
            PdfEntry(fullname="/path/2.pdf", size=200, hash="N/A"),
            PdfEntry(fullname="/path/3.pdf", size=300, hash="N/A")
        ]
        
        result = finder.detect_duplicates(entries)
        assert all(not entry.is_duplicate for entry in result)
    
    def test_ignore_empty_hash(self, finder):
        """Test that empty hashes are not considered duplicates."""
        entries = [
            PdfEntry(fullname="/path/1.pdf", size=100, hash=""),
            PdfEntry(fullname="/path/2.pdf", size=200, hash=""),
            PdfEntry(fullname="/path/3.pdf", size=300, hash="")
        ]
        
        result = finder.detect_duplicates(entries)
        assert all(not entry.is_duplicate for entry in result)
    
    def test_mixed_hashes(self, finder):
        """Test with mix of valid and N/A hashes."""
        entries = [
            PdfEntry(fullname="/path/1.pdf", size=100, hash="hash1"),
            PdfEntry(fullname="/path/2.pdf", size=200, hash="N/A"),
            PdfEntry(fullname="/path/3.pdf", size=300, hash="hash1"),  # Duplicate
            PdfEntry(fullname="/path/4.pdf", size=400, hash="")       # Empty hash
        ]
        
        result = finder.detect_duplicates(entries)
        
        assert result[0].is_duplicate is False
        assert result[1].is_duplicate is False  # N/A not duplicate
        assert result[2].is_duplicate is True   # Duplicate
        assert result[3].is_duplicate is False  # Empty hash not duplicate


class TestFinderSaveToCsv:
    """Tests for Finder.save_to_csv method."""
    
    def test_save_empty_list(self, finder, tmp_path):
        """Test saving an empty list to CSV."""
        output = tmp_path / "output.csv"
        finder.save_to_csv([], str(output))
        
        assert output.exists()
        content = output.read_text()
        assert "fullname" in content  # Header only
    
    def test_save_pdfs_to_csv(self, finder, tmp_path):
        """Test saving PDF entries to CSV."""
        entries = [
            PdfEntry(fullname="/path/1.pdf", size=100, hash="hash1", pages=5),
            PdfEntry(fullname="/path/2.pdf", size=200, hash="hash2", pages=10)
        ]
        
        output = tmp_path / "output.csv"
        finder.save_to_csv(entries, str(output))
        
        assert output.exists()
        
        # Read and verify CSV
        with open(output, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]["fullname"] == "/path/1.pdf"
        assert rows[0]["pages"] == "5"
        assert rows[1]["hash"] == "hash2"
    
    def test_save_with_duplicates(self, finder, tmp_path):
        """Test saving PDFs with duplicate flags."""
        entries = [
            PdfEntry(fullname="/path/1.pdf", size=100, hash="hash1", is_duplicate=False),
            PdfEntry(fullname="/path/2.pdf", size=200, hash="hash1", is_duplicate=True)
        ]
        
        output = tmp_path / "output.csv"
        finder.save_to_csv(entries, str(output))
        
        with open(output, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert rows[0]["is_duplicate"] == "False"
        assert rows[1]["is_duplicate"] == "True"


class TestFinderCopyFiles:
    """Tests for Finder.copy_files method."""
    
    def test_copy_single_file(self, temp_dir, sample_pdf_content, finder):
        """Test copying a single PDF file."""
        source = temp_dir / "test.pdf"
        source.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        entries = [PdfEntry(fullname=str(source), size=source.stat().st_size, hash="")]
        result = finder.copy_files(entries, str(destination))
        
        assert len(result) == 1
        dest_file = destination / "test.pdf"
        assert dest_file.exists()
    
    def test_copy_multiple_files(self, create_sample_pdfs, finder):
        """Test copying multiple PDF files."""
        source_dir = create_sample_pdfs[0].parent
        destination = source_dir / "dest"
        destination.mkdir()
        
        entries = [
            PdfEntry(fullname=str(create_sample_pdfs[0]), size=create_sample_pdfs[0].stat().st_size, hash=""),
            PdfEntry(fullname=str(create_sample_pdfs[1]), size=create_sample_pdfs[1].stat().st_size, hash="")
        ]
        
        result = finder.copy_files(entries, str(destination))
        assert len(result) == 2
    
    def test_copy_skip_duplicates(self, temp_dir, sample_pdf_content, finder):
        """Test that duplicates are skipped during copy."""
        # Create actual files
        source1 = temp_dir / "test1.pdf"
        source1.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        entries = [
            PdfEntry(fullname=str(source1), size=source1.stat().st_size, hash="", is_duplicate=False),
            PdfEntry(fullname=str(source1), size=source1.stat().st_size, hash="", is_duplicate=True)
        ]
        
        result = finder.copy_files(entries, str(destination))
        # First entry (not duplicate) should be copied, second (duplicate) skipped
        assert len(result) == 1
    
    def test_copy_with_overwrite(self, temp_dir, sample_pdf_content, finder):
        """Test copying with overwrite enabled."""
        source = temp_dir / "test.pdf"
        source.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        existing = destination / "test.pdf"
        existing.write_bytes(b"existing content")
        
        entries = [PdfEntry(fullname=str(source), size=source.stat().st_size, hash="")]
        
        # First copy
        finder.copy_files(entries, str(destination), overwrite=False)
        
        # Second copy with overwrite
        result = finder.copy_files(entries, str(destination), overwrite=True)
        assert len(result) == 1
    
    def test_copy_calls_callback(self, temp_dir, sample_pdf_content, finder):
        """Test that callback is called during copy."""
        source = temp_dir / "test.pdf"
        source.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        entries = [PdfEntry(fullname=str(source), size=source.stat().st_size, hash="")]
        mock_callback = Mock()
        mock_callback.is_cancelled.return_value = False
        
        finder.copy_files(entries, str(destination), callback=mock_callback)
        
        assert mock_callback.update.called
    
    def test_copy_skip_empty_files(self, temp_dir, finder):
        """Test that empty files are skipped during copy."""
        empty_pdf = temp_dir / "empty.pdf"
        empty_pdf.write_bytes(b"")
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        entries = [PdfEntry(fullname=str(empty_pdf), size=0, hash="")]
        result = finder.copy_files(entries, str(destination))
        
        assert len(result) == 0
    
    def test_copy_rename_with_metadata(self, temp_dir, sample_pdf_content, finder):
        """Test copying files with metadata-based renaming."""
        source = temp_dir / "test.pdf"
        source.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        entries = [
            PdfEntry(
                fullname=str(source),
                size=source.stat().st_size,
                hash="",
                info={"title": "My Document Title"}
            )
        ]
        
        result = finder.copy_files(entries, str(destination), rename_with_metadata=True)
        
        assert len(result) == 1
        dest_file = destination / "My Document Title.pdf"
        assert dest_file.exists()
    
    def test_copy_overwrite_remove_failure(self, temp_dir, sample_pdf_content, finder):
        """Test copy when remove of existing file fails."""
        source = temp_dir / "test.pdf"
        source.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        existing = destination / "test.pdf"
        existing.write_bytes(b"existing")
        
        entries = [PdfEntry(fullname=str(source), size=source.stat().st_size, hash="")]
        
        # Mock os.remove to simulate failure
        with patch('os.remove', side_effect=PermissionError("Cannot remove")):
            result = finder.copy_files(entries, str(destination), overwrite=True)
        
        # Copy should be skipped
        assert len(result) == 0
    
    def test_copy_exception_handling(self, temp_dir, sample_pdf_content, finder):
        """Test copy when shutil.copyfile fails."""
        source = temp_dir / "test.pdf"
        source.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        entries = [PdfEntry(fullname=str(source), size=source.stat().st_size, hash="")]
        mock_callback = Mock()
        mock_callback.is_cancelled.return_value = False
        
        # Mock shutil.copyfile to:
        # 1. Create the destination file (so os.path.exists returns True)
        # 2. Then raise an exception
        def side_effect_with_file_creation(src, dst):
            # Create the destination file so line 273 is covered
            with open(dst, 'w') as f:
                f.write("partial content")
            raise IOError("Copy failed")
        
        with patch('shutil.copyfile', side_effect=side_effect_with_file_creation):
            result = finder.copy_files(entries, str(destination), callback=mock_callback)
        
        # No files should be copied
        assert len(result) == 0
        
        # Callback should report failure
        assert mock_callback.update.called
        call_args = mock_callback.update.call_args
        assert call_args[0][0] == CALLBACK_FILE_COPIED
        assert "Failed to copy" in call_args[0][1]
    
    def test_copy_cancellation(self, temp_dir, sample_pdf_content, finder):
        """Test that copy stops when cancelled."""
        source1 = temp_dir / "test1.pdf"
        source1.write_bytes(sample_pdf_content)
        source2 = temp_dir / "test2.pdf"
        source2.write_bytes(sample_pdf_content)
        
        destination = temp_dir / "dest"
        destination.mkdir()
        
        entries = [
            PdfEntry(fullname=str(source1), size=source1.stat().st_size, hash=""),
            PdfEntry(fullname=str(source2), size=source2.stat().st_size, hash=""),
        ]
        
        mock_callback = Mock()
        mock_callback.is_cancelled.return_value = False
        call_count = [0]
        def should_cancel():
            call_count[0] += 1
            return call_count[0] >= 2
        mock_callback.is_cancelled.side_effect = should_cancel
        
        result = finder.copy_files(entries, str(destination), callback=mock_callback)
        # Should stop after copying first file (second iteration check cancels)
        assert len(result) == 1


class TestFinderConvertSize:
    """Tests for Finder.convert_size static method."""
    
    def test_convert_small_bytes(self, finder):
        """Test converting small bytes to KB."""
        result = finder.convert_size(500)
        # 500 // 1000 = 0 KB
        assert result == "0 KB"
    
    def test_convert_kb(self, finder):
        """Test converting KB to human-readable."""
        result = finder.convert_size(5000)
        # 5000 // 1000 = 5 KB
        assert result == "5 KB"
    
    def test_convert_mb(self, finder):
        """Test converting MB to human-readable."""
        result = finder.convert_size(1048576)
        # 1048576 // 1000 = 1048 KB, 1048 > 1000, so 1048/1000 = 1.0 MB
        assert result == "1.0 MB"
    
    def test_convert_large_value(self, finder):
        """Test converting large file size."""
        result = finder.convert_size(5242880)
        # 5242880 // 1000 = 5242 KB, 5242 > 1000, so 5242/1000 = 5.2 MB
        assert "MB" in result


class TestFinderSanitizeFilename:
    """Tests for Finder._sanitize_filename private method."""
    
    def test_sanitize_normal_filename(self, finder):
        """Test sanitizing a normal filename."""
        result = finder._sanitize_filename("normal.pdf")
        assert result == "normal.pdf"
    
    def test_sanitize_invalid_chars(self, finder):
        """Test sanitizing filename with invalid characters."""
        result = finder._sanitize_filename("file:<>\"/\\|?*?.pdf")
        assert ":" not in result
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert "/" not in result
        assert "\\" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result
    
    def test_sanitize_leading_dots_spaces(self, finder):
        """Test sanitizing filename with leading dots and spaces."""
        result = finder._sanitize_filename("   .file.pdf")
        assert result == "file.pdf"
    
    def test_sanitize_empty_result(self, finder):
        """Test sanitizing filename that becomes empty."""
        result = finder._sanitize_filename("...")
        assert result == "untitled"


class TestFinderCalculateHash:
    """Tests for Finder._calculate_hash private method."""
    
    def test_calculate_hash(self, temp_dir, sample_pdf_content, finder):
        """Test calculating hash for a file."""
        pdf = temp_dir / "test.pdf"
        pdf.write_bytes(sample_pdf_content)
        
        result = finder._calculate_hash(str(pdf))
        assert result != ""
        assert isinstance(result, str)
        assert len(result) == 16  # xxh64 produces 16-char hex string
    
    def test_calculate_hash_deterministic(self, temp_dir, sample_pdf_content, finder):
        """Test that hash calculation is deterministic."""
        pdf = temp_dir / "test.pdf"
        pdf.write_bytes(sample_pdf_content)
        
        hash1 = finder._calculate_hash(str(pdf))
        hash2 = finder._calculate_hash(str(pdf))
        
        assert hash1 == hash2


class TestFinderReadPdfInfo:
    """Tests for Finder._read_pdf_info private method."""
    
    def test_read_pdf_info_skips_invalid(self, temp_dir, finder):
        """Test that invalid PDFs raise an exception."""
        invalid_pdf = temp_dir / "invalid.pdf"
        invalid_pdf.write_bytes(b"this is not a valid PDF")
        
        entry = PdfEntry(fullname=str(invalid_pdf), size=invalid_pdf.stat().st_size, hash="")
        
        with pytest.raises(Exception):
            finder._read_pdf_info(entry)
    
    def test_read_pdf_info_updates_entry(self, temp_dir, finder, sample_pdf_content):
        """Test that _read_pdf_info updates the entry in place (integration test)."""
        # Create a valid PDF using PyPDF2
        from PyPDF2 import PdfWriter
        
        pdf_writer = PdfWriter()
        pdf_writer.add_blank_page(width=612, height=792)
        
        pdf_path = temp_dir / "test.pdf"
        with open(pdf_path, "wb") as f:
            pdf_writer.write(f)
        
        entry = PdfEntry(fullname=str(pdf_path), size=pdf_path.stat().st_size, hash="")
        
        # Call without try/except to ensure return statement is reached
        result = finder._read_pdf_info(entry)
        # If PDF is valid, pages should be set
        assert result.pages is not None or result.pages == 0  # May be 0 if parsing fails
        assert result.info is not None
        # Verify the entry is returned (line 302 coverage)
        assert result is entry


class TestFinderGetCurrentFolder:
    """Tests for Finder.get_current_folder static method."""
    
    def test_get_current_folder(self):
        """Test getting current folder."""
        result = Finder.get_current_folder()
        assert isinstance(result, str)
        assert os.path.isabs(result)


class TestCallBack:
    """Tests for CallBack class."""
    
    def test_callback_update(self):
        """Test CallBack update method."""
        callback = CallBack()
        # Should not raise an exception
        callback.update(1, "Test message")


class TestIntegration:
    """Integration tests for the full workflow."""
    
    def test_full_workflow_with_mocks(self, finder, tmp_path, create_sample_pdfs):
        """Test the complete workflow with mocked validation."""
        # Create actual PDFs for find and copy operations
        source_dir = create_sample_pdfs[0].parent
        
        # 1. Find all PDFs
        pdf_files = finder.find_all_pdf_files(str(source_dir))
        assert len(pdf_files) == 2
        
        # 2. Validate with mocked _read_pdf_info
        with patch.object(finder, '_read_pdf_info', return_value=None):
            validated = finder.validate_pdfs(pdf_files)
            assert len(validated) == 2
        
        # 3. Detect duplicates (no actual duplicates in this test)
        with_duplicates = finder.detect_duplicates(validated)
        duplicates = [e for e in with_duplicates if e.is_duplicate]
        assert len(duplicates) == 0
        
        # 4. Save to CSV
        csv_path = tmp_path / "output.csv"
        finder.save_to_csv(with_duplicates, str(csv_path))
        assert csv_path.exists()
        
        # 5. Copy only non-duplicates
        destination = tmp_path / "dest"
        destination.mkdir()
        non_duplicates = [e for e in with_duplicates if not e.is_duplicate]
        copied = finder.copy_files(non_duplicates, str(destination))
        assert len(copied) == 2
