"""
Integration Tests for paths Examples

Validates the examples in suitkaise/_docs_copy/paths/examples.md
with detailed assertions.
"""

import json
import sqlite3
import threading
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import paths
from suitkaise.paths import (
    AnyPath,
    CustomRoot,
    PathDetectionError,
    Skpath,
    autopath,
    is_valid_filename,
    streamline_path,
    streamline_path_quick,
)


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def run_test(self, name: str, test_func):
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*70}{self.RESET}\n")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        for result in self.results:
            status = f"{self.GREEN}✓ PASS{self.RESET}" if result.passed else f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")

        if failed != 0:
            print(f"{self.BOLD}{self.RED}Failed tests (recap):{self.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  {self.RED}✗ {result.name}{self.RESET}")
                    if result.error:
                        print(f"     {self.RED}└─ {result.error}{self.RESET}")
            print()

        try:
            from tests._failure_registry import record_failures
            record_failures(self.suite_name, [r for r in self.results if not r.passed])
        except Exception:
            pass

        return failed == 0


# =============================================================================
# Tests
# =============================================================================

def test_paths_basic_current_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            current_file = Skpath()
            assert current_file.ap
            assert current_file.name
            assert current_file.rp == ""


def test_paths_current_directory() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            current_dir = Skpath().parent
            config_file = current_dir / "config.json"
            config_file.write_text("{}")
            assert config_file.exists


def test_paths_helper_functions() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            current_file = paths.get_caller_path()
            current_dir = paths.get_current_dir()
            cwd = paths.get_cwd()
            assert current_file
            assert current_dir
            assert cwd


def test_paths_project_root_detection() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "pyproject.toml").write_text("[build-system]")
        with CustomRoot(tmp_path):
            root = paths.get_project_root()
            assert root.ap.endswith(tmp_path.as_posix())
            some_file = Skpath("src/main.py")
            assert some_file.root.ap == root.ap


def test_paths_custom_root_override() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        custom_root = tmp_path / "custom"
        custom_root.mkdir()
        paths.set_custom_root(custom_root)
        assert paths.get_project_root().ap.endswith("custom")
        paths.clear_custom_root()
        with CustomRoot(custom_root):
            assert paths.get_project_root().ap.endswith("custom")


def test_paths_joining_and_properties() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            root = Skpath().root
            data_file = root / "data" / "users.json"
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text("{}")
            assert isinstance(data_file, Skpath)
            assert data_file.ap.endswith("/data/users.json")
            assert data_file.rp.endswith("data/users.json")


def test_paths_core_properties() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            root = Skpath().root
            path = root / "src/utils/helpers.py"
            assert path.ap.endswith("/src/utils/helpers.py")
            assert path.rp.endswith("src/utils/helpers.py")
            assert path.platform
            assert path.id
            assert Skpath(path.id).rp == path.rp


def test_paths_pathlib_compat() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            root = Skpath().root
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "main.py").write_text("print('hi')")
            path = Skpath(root / "src" / "main.py")
            assert path.name == "main.py"
            assert path.stem == "main"
            assert path.suffix == ".py"
            assert path.parent.rp.endswith("src")
            assert path.exists


def test_paths_file_operations() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            root = Skpath().root
            new_dir = root / "output/reports"
            new_dir.mkdir(parents=True, exist_ok=True)
            new_file = new_dir / "report.txt"
            new_file.touch()
            source = root / "data/input.csv"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("a,b")
            dest = source.copy_to(root / "backup/input.csv", parents=True)
            assert dest.exists
            final = source.move_to(root / "data/final.json", overwrite=True)
            assert final.exists
            old_file = root / "temp/old.txt"
            old_file.parent.mkdir(parents=True, exist_ok=True)
            old_file.write_text("x")
            old_file.unlink(missing_ok=True)
            empty_dir = root / "temp/empty"
            empty_dir.mkdir(parents=True, exist_ok=True)
            empty_dir.rmdir()


def test_paths_cross_platform() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            path = Skpath("data\\subdir\\file.txt")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("content")
            assert "/" in path.ap
            assert path.platform


def test_paths_validation_and_streamline() -> None:
    assert is_valid_filename("my_file.txt") is True
    assert is_valid_filename("file<name>.txt") is False
    assert is_valid_filename("CON") is False
    assert is_valid_filename("") is False

    clean = streamline_path("My File<1>.txt", chars_to_replace=" ")
    assert " " not in clean
    quick = streamline_path_quick("My File наме.txt")
    assert " " not in quick
    short = streamline_path("Very Long Filename.txt", max_len=10, chars_to_replace=" ")
    assert short.endswith(".txt")


def test_paths_project_structure() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.py").write_text("print('x')")
            (tmp_path / "tests").mkdir()
            all_paths = paths.get_project_paths()
            assert any(p.rp.endswith("src/main.py") for p in all_paths)
            structure = paths.get_project_structure()
            assert structure
            tree = paths.get_formatted_project_tree(depth=2)
            assert "src" in tree


def test_paths_module_path() -> None:
    import json as json_module
    json_path = paths.get_module_path(json_module)
    assert json_path.exists


def test_paths_thread_safety() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            results: list[dict] = []

            def worker(worker_id: int):
                path = Skpath(f"data/file_{worker_id}.txt")
                results.append({"id": worker_id, "ap": path.ap, "rp": path.rp})

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert len(results) == 5


def test_autopath_basic() -> None:
    @autopath()
    def process_file(path: Skpath) -> str:
        return path.ap

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.py").write_text("x")
            assert "main.py" in process_file("src/main.py")


def test_autopath_target_types() -> None:
    @autopath()
    def needs_skpath(path: Skpath) -> str:
        return path.rp

    @autopath()
    def needs_path(path: Path) -> str:
        return str(path)

    @autopath()
    def needs_string(path: str) -> str:
        return path

    @autopath()
    def needs_anypath(path: AnyPath) -> str:
        return path.rp

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.py").write_text("x")
            abs_path = str(tmp_path / "src" / "main.py")
            assert needs_skpath(abs_path).endswith("src/main.py")
            assert "main.py" in needs_path(abs_path)
            assert needs_string(abs_path).endswith("src/main.py")
            assert needs_anypath(abs_path).endswith("src/main.py")


def test_autopath_lists() -> None:
    @autopath()
    def process_files(paths_list: list[Skpath]) -> list[str]:
        return [p.rp for p in paths_list]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            result = process_files([
                str(tmp_path / "src/a.py"),
                str(tmp_path / "src/b.py"),
                str(tmp_path / "src/c.py"),
            ])
            assert result == ["src/a.py", "src/b.py", "src/c.py"]


def test_autopath_use_caller() -> None:
    @autopath(use_caller=True)
    def log_location(message: str, path: Skpath = None):
        return f"[{path.rp}] {message}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            message = log_location("Starting process")
            assert "Starting process" in message


def test_autopath_only_option() -> None:
    @autopath(only="file_path")
    def process(file_path: str, tags: list[str], ids: list[str]):
        return file_path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            result = process("src/main.py", tags=["python"], ids=["abc"])
            assert result.endswith("src/main.py")


def test_paths_store_ids_in_db() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            conn = sqlite3.connect(":memory:")
            conn.execute("""
                CREATE TABLE files (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    size INTEGER,
                    processed BOOLEAN
                )
            """)

            def store_file(path: Skpath, size: int):
                conn.execute(
                    "INSERT INTO files (id, name, size, processed) VALUES (?, ?, ?, ?)",
                    (path.id, path.name, size, False)
                )

            file_path = Skpath(tmp_path / "data/input.csv")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("a,b")
            store_file(file_path, file_path.stat.st_size)
            conn.commit()

            def get_unprocessed_files() -> list[Skpath]:
                cursor = conn.execute("SELECT id FROM files WHERE processed = 0")
                return [Skpath(row[0]) for row in cursor.fetchall()]

            files = get_unprocessed_files()
            assert files[0].rp.endswith("data/input.csv")


def test_paths_cache_with_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            cache_dir = Path(tmp_path / ".cache")
            cache_dir.mkdir(exist_ok=True)

            def get_cached_result(source_path: Skpath) -> dict | None:
                cache_file = cache_dir / f"{source_path.id}.json"
                if cache_file.exists():
                    return json.loads(cache_file.read_text())
                return None

            def save_cached_result(source_path: Skpath, result: dict):
                cache_file = cache_dir / f"{source_path.id}.json"
                cache_file.write_text(json.dumps(result))

            def process_with_cache(path: Skpath) -> dict:
                cached = get_cached_result(path)
                if cached is not None:
                    return cached
                result = {"size": path.stat.st_size}
                save_cached_result(path, result)
                return result

            source_path = Skpath("data/file.txt")
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text("hello")
            result = process_with_cache(source_path)
            assert result["size"] == 5
            assert get_cached_result(source_path) == result


def test_paths_build_file_index() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.py").write_text("x")

            @dataclass
            class FileInfo:
                path: Skpath
                size: int

            def build_index(root: Skpath = None, extensions: list[str] = None) -> list[FileInfo]:
                if root is None:
                    root = paths.get_project_root()
                index = []
                for file_path in paths.get_project_paths(root=root):
                    if not file_path.is_file:
                        continue
                    if extensions and file_path.suffix not in extensions:
                        continue
                    index.append(FileInfo(path=file_path, size=file_path.stat.st_size))
                return index

            index = build_index(extensions=[".py"])
            assert any(info.path.rp.endswith("src/main.py") for info in index)


def test_paths_config_loader() -> None:
    class ConfigLoader:
        def __init__(self, config_path: AnyPath):
            self.config_path = Skpath(config_path)
            self.config_dir = self.config_path.parent
            self.config = self._load()

        def _load(self) -> dict:
            with open(self.config_path, "r") as f:
                return json.load(f)

        def resolve_path(self, relative_path: str) -> Skpath:
            return self.config_dir / relative_path

        def get_data_dir(self) -> Skpath:
            data_dir = self.config.get("data_dir", "data")
            return self.resolve_path(data_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            config_path = Skpath(tmp_path / "configs/production.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps({"data_dir": "./data"}))
            loader = ConfigLoader(config_path)
            assert loader.get_data_dir().rp.endswith("configs/data")


def test_paths_full_script() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with CustomRoot(tmp_path):
            class FileOrganizer:
                def __init__(self, output_dir: AnyPath = None):
                    try:
                        self.project_root = paths.get_project_root()
                    except PathDetectionError:
                        self.project_root = paths.get_cwd()
                    self.output_dir = Skpath(output_dir) if output_dir else self.project_root / "organized"
                    self.output_dir.mkdir(parents=True, exist_ok=True)

                def organize(self, source_dir: Skpath):
                    files = list(source_dir.rglob("*"))
                    organized = 0
                    for file_path in files:
                        if not file_path.is_file:
                            continue
                        dest = self.output_dir / file_path.name
                        file_path.copy_to(dest, overwrite=True)
                        organized += 1
                    return organized

            source_dir = Skpath("downloads")
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "notes.txt").write_text("notes")
            organizer = FileOrganizer(output_dir=Skpath("organized"))
            organized = organizer.organize(source_dir)
            assert organized == 1


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    runner = TestRunner("Integration - paths Examples")

    runner.run_test("Basic current file", test_paths_basic_current_file)
    runner.run_test("Current directory", test_paths_current_directory)
    runner.run_test("Helper functions", test_paths_helper_functions)
    runner.run_test("Project root detection", test_paths_project_root_detection)
    runner.run_test("Custom root override", test_paths_custom_root_override)
    runner.run_test("Joining and properties", test_paths_joining_and_properties)
    runner.run_test("Core properties", test_paths_core_properties)
    runner.run_test("Pathlib compat", test_paths_pathlib_compat)
    runner.run_test("File operations", test_paths_file_operations)
    runner.run_test("Cross-platform paths", test_paths_cross_platform)
    runner.run_test("Validation + streamline", test_paths_validation_and_streamline)
    runner.run_test("Project structure", test_paths_project_structure)
    runner.run_test("Module path", test_paths_module_path)
    runner.run_test("Thread safety", test_paths_thread_safety)
    runner.run_test("autopath basic", test_autopath_basic)
    runner.run_test("autopath target types", test_autopath_target_types)
    runner.run_test("autopath lists", test_autopath_lists)
    runner.run_test("autopath use_caller", test_autopath_use_caller)
    runner.run_test("autopath only option", test_autopath_only_option)
    runner.run_test("Store IDs in DB", test_paths_store_ids_in_db)
    runner.run_test("Cache with IDs", test_paths_cache_with_ids)
    runner.run_test("Build file index", test_paths_build_file_index)
    runner.run_test("Config loader", test_paths_config_loader)
    runner.run_test("Full script", test_paths_full_script)

    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
