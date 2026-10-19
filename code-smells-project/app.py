"""Entry point; use `flask --app app:create_app init-db` antes do primeiro boot."""
import os
from loja import create_app

if __name__ == '__main__':
    application = create_app()
    application.run(host=os.environ.get('APP_HOST', '127.0.0.1'),
                    port=int(os.environ.get('APP_PORT', '5000')), debug=False, use_reloader=False)
