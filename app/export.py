import csv, io
from flask import Response


def export_csv(headers, rows, filename):
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    output.seek(0)
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
