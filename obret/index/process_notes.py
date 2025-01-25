import re
from pathlib import Path

import yaml

from obret.config.config_loader import load_base_config
from obret.utils.file_io import save_pickle


def split_frontmatter_and_text(note_text: str) -> tuple:
    frontmatter_regex = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = frontmatter_regex.match(note_text)
    if match:
        frontmatter = match.group(1)
        text = note_text[match.end() :]
        frontmatter_dict = yaml.safe_load(frontmatter)
        return frontmatter_dict, text
    else:
        return {}, note_text


def process_notes(vault_dirpath: Path, exclude_dirnames: list[str]) -> dict:
    vault_dict = {}
    exclude_dirnames_set = set(exclude_dirnames)
    note_filepaths = []

    for dirpath in vault_dirpath.iterdir():
        if dirpath.is_dir() and dirpath.name not in exclude_dirnames_set:
            note_filepaths.extend(dirpath.glob("**/*.md"))

    for i, note_filepath in enumerate(note_filepaths, 1):
        docno = str(i)
        note = note_filepath.read_text()
        _frontmatter, text = split_frontmatter_and_text(note)

        vault_dict[docno] = {
            "rel_filepath": str(note_filepath.relative_to(vault_dirpath)),
            "title": note_filepath.stem,
            "text": text,
        }
    return vault_dict


def main():
    base_config = load_base_config()

    vault_dict = process_notes(base_config.vault_dirpath, base_config.exclude_dirnames)
    print(f"Number of notes: {len(vault_dict)}")
    save_pickle(vault_dict, base_config.vault_dict_filepath)
    print(f"Saved vault dictionary to {base_config.vault_dict_filepath}")


if __name__ == "__main__":
    main()
