import csv
from pathlib import Path

input_csv = "E:\dfdc_new\\test.csv"
output_csv = "E:\dfdc_new\\test_new.csv"

with open(input_csv, newline="", encoding="utf-8") as fin, \
     open(output_csv, "w", newline="", encoding="utf-8") as fout:
    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
    writer.writeheader()

    for row in reader:
        name = Path(row["filename"])
        if name.suffix.lower() == ".mp4":
            row["filename"] = name.with_suffix(".avi").as_posix()
        writer.writerow(row)

print(f"done -> {output_csv}")
