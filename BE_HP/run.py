from app import create_app
from app.extensions import socketio
from scripts.seed_data import main

app = create_app()

if __name__ == "__main__":
    main()
    socketio.run(app, debug=True)