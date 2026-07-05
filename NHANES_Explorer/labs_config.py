"""
labs_config.py
==============
Central configuration for the Lab Correlation tool.

This file lives at the project root alongside manage.py.
Set REFERENCE_RANGES_PATH to your reference_ranges.csv.
The XPT data folder is shared with the Export tool and is
set at runtime via the app UI (stored in the Django session).

If you want to hardcode the XPT data path instead of using
the session, set XPT_DATA_PATH here and it will take precedence.
"""

from pathlib import Path

# Absolute path to reference_ranges.csv
REFERENCE_RANGES_PATH = Path(__file__).resolve().parent / 'reference_ranges.csv'

# Optional: hardcode XPT data folder (overrides session value if set)
# XPT_DATA_PATH = Path('/absolute/path/to/your/data/folder')
XPT_DATA_PATH = None

# Minimum number of rows required in a group (normal/high/low)
# before a correlation test is run for that group
MIN_GROUP_SIZE = 30

# Maximum number of independent variables allowed per run
MAX_INDEPENDENT_VARS = 50
