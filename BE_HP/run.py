
from app import create_app
from scripts.seed_data import main

app = create_app("dev")

if __name__ == "__main__":
    main()
    app.run(debug=True)
