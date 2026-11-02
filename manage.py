import os
from app import create_app

# Hosting services set FLASK_CONFIG=production; running this file locally uses development mode
app= create_app(os.environ.get('FLASK_CONFIG', 'development'))


if __name__=='__main__':
    app.run(debug=app.debug)
