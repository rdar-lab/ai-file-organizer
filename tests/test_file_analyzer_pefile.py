import types


class DummyStringTable:
    def __init__(self, entries):
        # entries is a dict of bytes->bytes
        self.entries = entries


class DummyFileInfo:
    def __init__(self, key=None, string_tables=None):
        # Key should be bytes like b"StringFileInfo"
        self.Key = key
        self.StringTable = string_tables or []


class DummyPE:
    def __init__(self, fileinfo):
        # fileinfo can be list/tuple or objects
        self.FileInfo = fileinfo

    def parse_data_directories(self, directories=None):
        pass

    def close(self):
        pass


def file_analyzer(monkeypatch, fake_pe):
    # Monkeypatch the pefile module inside the file_analyzer module so the function uses our fake PE
    fake_pe_module = types.SimpleNamespace(PE=lambda *args, **kwargs: fake_pe,
                                           DIRECTORY_ENTRY={"IMAGE_DIRECTORY_ENTRY_RESOURCE": 2})
    import ai_file_organizer.file_analyzer as fa
    monkeypatch.setattr(fa, "pefile", fake_pe_module)
    monkeypatch.setattr(fa, "PEFILE_AVAILABLE", True)

    return fa.FileAnalyzer()


def test_get_executable_metadata_handles_list_fileinfo(monkeypatch, tmp_path):
    # Prepare a fake PE structure where FileInfo contains a list
    entries = {b"ProductName": b"TestProduct        ", b"FileVersion": b"1.2.3      "}
    st = DummyStringTable(entries)
    fi = DummyFileInfo(key=b"StringFileInfo", string_tables=[st])
    # Wrap fi in a list inside FileInfo to simulate nested list scenario
    fake_pe = DummyPE(fileinfo=[[fi]])
    fa = file_analyzer(monkeypatch, fake_pe)

    # Now call the _get_executable_metadata with a temp file path
    temp_file = tmp_path / "dummy.exe"
    temp_file.write_text("dummy")

    # Ensure function returns expected metadata
    metadata = fa._get_executable_metadata(str(temp_file))
    assert metadata is not None
    assert metadata.get("ProductName") == "TestProduct"
    assert metadata.get("FileVersion") == "1.2.3"


def test_get_executable_metadata_skips_non_stringfileinfo(monkeypatch, tmp_path):
    # Prepare a fake PE where FileInfo has an entry with a different Key
    entries = {b"ProductName": b"OtherProduct       "}
    st = DummyStringTable(entries)
    fi_good = DummyFileInfo(key=b"StringFileInfo", string_tables=[st])
    fi_bad = DummyFileInfo(key=b"VarFileInfo", string_tables=[st])
    fake_pe = DummyPE(fileinfo=[fi_bad, fi_good])
    fa = file_analyzer(monkeypatch, fake_pe)

    temp_file = tmp_path / "dummy2.exe"
    temp_file.write_text("dummy")

    metadata = fa._get_executable_metadata(str(temp_file))
    assert metadata is not None
    assert metadata.get("ProductName") == "OtherProduct" or metadata.get("ProductName") == "OtherProduct"
