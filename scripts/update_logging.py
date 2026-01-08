#!/usr/bin/env python3
"""
Скрипт для массовой замены logging на loguru во всех модулях.
"""

import re
from pathlib import Path


def update_file(file_path: Path) -> bool:
    """Обновляет один файл."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content
        
        # Пропускаем уже обновленные файлы
        if "from app.utils.logger import" in content:
            return False
        
        # Пропускаем сам logger.py
        if "app/utils/logger.py" in str(file_path):
            return False
        
        # Заменяем import logging на get_logger
        if re.search(r"^import logging$", content, re.MULTILINE):
            # Находим последний импорт из app
            app_imports = list(re.finditer(r"^from app\.[^\n]+$", content, re.MULTILINE))
            
            if app_imports:
                # Добавляем после последнего импорта из app
                last_import = app_imports[-1]
                insert_pos = last_import.end()
                content = content[:insert_pos] + "\nfrom app.utils.logger import get_logger" + content[insert_pos:]
            else:
                # Заменяем import logging
                content = re.sub(
                    r"^import logging$",
                    "from app.utils.logger import get_logger",
                    content,
                    flags=re.MULTILINE,
                    count=1
                )
        
        # Заменяем logger = logging.getLogger(...)
        content = re.sub(
            r"logger = logging\.getLogger\(([^)]+)\)",
            r"logger = get_logger(\1)",
            content
        )
        
        # Удаляем import logging если он больше не нужен
        if "logging." not in content and "logging import" not in content:
            content = re.sub(r"^import logging\n", "", content, flags=re.MULTILINE)
        
        if content != original:
            file_path.write_text(content, encoding="utf-8")
            print(f"✓ {file_path.relative_to(Path.cwd())}")
            return True
        
        return False
        
    except Exception as e:
        print(f"✗ Ошибка в {file_path}: {e}")
        return False


def main():
    """Обновляет все Python файлы в проекте."""
    project_root = Path(__file__).parent.parent / "project"
    
    # Список файлов для обновления
    patterns = [
        "app/modules/**/*.py",
        "app/api/**/*.py",
        "app/integrations/**/*.py",
        "app/bot/**/*.py",
        "app/account/**/*.py",
    ]
    
    updated = 0
    total = 0
    
    for pattern in patterns:
        for file_path in project_root.glob(pattern):
            if file_path.is_file() and "__pycache__" not in str(file_path):
                total += 1
                if update_file(file_path):
                    updated += 1
    
    print(f"\n✅ Обновлено: {updated}/{total} файлов")


if __name__ == "__main__":
    main()
