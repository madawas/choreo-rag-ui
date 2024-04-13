from typing import Union, Optional

from pydantic import DirectoryPath, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    def __init__(self):
        super().__init__(_env_file=".env", _env_file_encoding="utf-8")

    doc_upload_dir: DirectoryPath = Field(default="/home/uploads")
    backend_base_path: Optional[Union[str, None]] = None
