import os
from flask import Flask, url_for
from config import config_options

def create_app(config_name):

    app=Flask(__name__)

    app.config.from_object(config_options[config_name])

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Add each file's modified time to its URL so browsers fetch new CSS/JS after a change
    @app.context_processor
    def static_helpers():
        def versioned_static(filename):
            path=os.path.join(app.static_folder, filename)
            return url_for('static', filename=filename, v=int(os.path.getmtime(path)))
        return dict(versioned_static=versioned_static)

    return app