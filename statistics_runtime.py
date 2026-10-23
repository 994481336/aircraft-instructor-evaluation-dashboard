"""Load the statistics implementation by source version during Streamlit updates."""

from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from threading import RLock
from types import ModuleType


_load_lock = RLock()


def load_statistics() -> ModuleType:
    path = Path(__file__).with_name("instructor_statistics.py")
    source = path.read_bytes()
    name = f"_instructor_statistics_{sha256(source).hexdigest()}"
    with _load_lock:
        if name in sys.modules:
            return sys.modules[name]
        spec = spec_from_file_location(name, path)
        if spec is None:
            raise ImportError(f"Cannot load dashboard statistics from {path.name}")
        module = module_from_spec(spec)
        # Compile these exact bytes, not timestamp-based bytecode or a module
        # retained by an existing Streamlit worker. No uploaded data is executed.
        exec(compile(source, str(path), "exec"), module.__dict__)
        sys.modules[name] = module
        return module
