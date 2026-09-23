"""Load local configuration before importing application modules."""
from pathlib import Path

from dotenv import load_dotenv


# Resolve from the project, independent of the launcher's working directory.
# Explicit process environment variables take precedence over the local file.
load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False, encoding='utf-8-sig')
