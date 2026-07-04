import init_db
from template_fixes_010 import apply_template_fixes


def main():
    init_db.main()
    applied = apply_template_fixes()
    if applied:
        print("Applied built-in template fixes migration 010")


if __name__ == "__main__":
    main()
