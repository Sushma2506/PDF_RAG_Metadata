import sys
import tkinter as tk
from tkinter import filedialog

def pick_file() -> list:
    """
    Opens a GUI file picker window.
    Allows selecting MULTIPLE files at once.
    Returns a list of selected file paths.
    Exits the program if no file is selected.
    """
    supported_types = [
        ("All supported files", "*.pdf *.docx *.pptx *.html *.htm *.txt"),
        ("PDF files", "*.pdf"),
        ("Word documents", "*.docx"),
        ("PowerPoint files", "*.pptx"),
        ("HTML files", "*.html *.htm"),
        ("Text files", "*.txt"),
        ("All files", "*.*"),
    ]

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print("📂 Opening file picker — hold Ctrl to select multiple files...")

    # ← askopenfilenames (plural) allows multiple selection
    selected_paths = filedialog.askopenfilenames(
        title="Select one or more documents to index",
        filetypes=supported_types,
    )

    root.destroy()

    if not selected_paths:
        print("❌ No file selected. Exiting.")
        sys.exit(0)

    print(f"✅ {len(selected_paths)} file(s) selected:")
    for path in selected_paths:
        print(f"   → {path}")

    return list(selected_paths)  # returns a LIST of paths
