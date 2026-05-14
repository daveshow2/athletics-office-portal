import traceback
import sys

try:
    from app import app
    import api
    import models
    import analytics
    with app.app_context():
        import evaluate_system
    with open("import_error.txt", "w") as f:
        f.write("Success")
except Exception as e:
    with open("import_error.txt", "w") as f:
        f.write(traceback.format_exc())
