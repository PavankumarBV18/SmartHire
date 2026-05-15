
import sys
try:
    import flask
    with open('flask_success.txt', 'w') as f:
        f.write('Flask is installed ' + flask.__version__)
except ImportError as e:
    with open('flask_error.txt', 'w') as f:
        f.write(str(e))
except Exception as e:
    with open('check_error.txt', 'w') as f:
        f.write(str(e))
