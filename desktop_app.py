import threading
import webview

from app import run_flask  # import the function from app.py


def start_server():
    # Run the Flask app (this also initializes the DB)
    run_flask()


if __name__ == "__main__":
    # Start Flask in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Create native desktop window pointing to local server
    webview.create_window("AgencyOS | Owner Tracker", "http://127.0.0.1:5000")
    webview.start()
