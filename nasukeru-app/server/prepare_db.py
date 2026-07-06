import init_db
from template_fixes_010 import apply_template_fixes
from template_fixes_011 import apply_neuro_common_alignment


def main():
    init_db.main()
    applied = apply_template_fixes()
    if applied:
        print("Applied built-in template fixes migration 010")
    aligned = apply_neuro_common_alignment()
    if aligned:
        print("Applied neuro_common alignment migration 011")


if __name__ == "__main__":
    main()
