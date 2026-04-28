import os
import re
import statistics

def get_heading_distances(text: str):
    """
    Возвращает список расстояний между подзаголовками '##' (в символах и строках)
    """
    matches = list(re.finditer(r'^##\s+', text, re.MULTILINE))
    if len(matches) < 2:
        return [], []

    # Расстояния в символах
    distances_chars = [
        matches[i + 1].start() - matches[i].start()
        for i in range(len(matches) - 1)
    ]

    # Расстояния в строках
    lines = text.splitlines()
    heading_lines = [i for i, line in enumerate(lines) if line.strip().startswith("##")]
    distances_lines = [
        heading_lines[i + 1] - heading_lines[i]
        for i in range(len(heading_lines) - 1)
    ]

    return distances_chars, distances_lines


def analyze_markdown_folder(folder_path: str):
    """
    Проходит по всем .md-файлам в папке и считает медиану расстояния между подзаголовками '##'
    """
    all_medians_chars = []
    all_medians_lines = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.endswith(".md"):
                continue

            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            distances_chars, distances_lines = get_heading_distances(text)

            if distances_chars and distances_lines:
                median_chars = statistics.median(distances_chars)
                median_lines = statistics.median(distances_lines)

                all_medians_chars.append(median_chars)
                all_medians_lines.append(median_lines)

                print(f"📘 {file}")
                print(f" - Подзаголовков: {len(distances_chars) + 1}")
                print(f" - Медиана расстояния: {median_chars:.0f} символов / {median_lines:.0f} строк\n")
            else:
                print(f"⚠️ {file}: недостаточно подзаголовков для анализа\n")

    if all_medians_chars:
        overall_median_chars = statistics.median(all_medians_chars)
        overall_median_lines = statistics.median(all_medians_lines)

        print("=" * 60)
        print(f"📊 Общая медиана по папке '{os.path.basename(folder_path)}':")
        print(f" - В символах: {overall_median_chars:.0f}")
        print(f" - В строках:  {overall_median_lines:.0f}")
        print("\n💡 Рекомендация: размер чанка можно взять ≈ {overall_median_chars:.0f} символов "
              f"(или {overall_median_lines:.0f} строк).")
    else:
        print("❌ В папке не найдено файлов с подходящими подзаголовками.")


if __name__ == "__main__":
    # 🔹 Папка с твоей базой знаний
    folder_path = "knowledge_base"
    analyze_markdown_folder(folder_path)