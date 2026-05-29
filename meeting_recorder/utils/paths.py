import os
import sys

def get_base_path():
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS for internal resources.
        # However, for user-editable files like .env or recordings, we want the path 
        # relative to the ACTUAL EXE location.
        return os.path.dirname(sys.executable)
    
    # In development, use the project root (3 levels up from this file)
    current_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

def get_resource_path(relative_path):
    """Get path to internal bundled resource."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(get_base_path(), relative_path)
