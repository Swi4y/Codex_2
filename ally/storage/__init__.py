"""Storage backend registry.

Only a plain file-based store is supported to avoid binary databases.
"""

from .file_store import FileStorage


def get_storage(kind: str = "files", path: str = "data") -> FileStorage:
    """Return a storage instance.

    Parameters
    ----------
    kind: str
        Currently only ``"files"`` is allowed.
    path: str
        Directory for the storage data.
    """
    if kind != "files":
        raise ValueError("only 'files' backend supported")
    return FileStorage(path)
