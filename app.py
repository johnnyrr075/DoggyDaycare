"""Application entry point for the Doggy Daycare web UI."""

from doggydaycare.webapp import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
