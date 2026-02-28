"""Start ngrok tunnel and auto-set the webhook URL."""

import sys
import time

from pyngrok import ngrok, conf

from app.config import settings


def start_tunnel():
    """Start ngrok tunnel on port 8000.

    Prints the public URL for webhook configuration.
    """
    if settings.ngrok_auth_token:
        conf.get_default().auth_token = settings.ngrok_auth_token

    # Open tunnel
    tunnel = ngrok.connect(settings.port, "http")
    public_url = tunnel.public_url

    # Force HTTPS
    if public_url.startswith("http://"):
        public_url = public_url.replace("http://", "https://")

    print("\n" + "=" * 60)
    print("  🚇 ngrok tunnel active")
    print(f"  📡 Public URL:  {public_url}")
    print(f"  🪝 Webhook URL: {public_url}/webhook")
    print(f"  🔑 Verify Token: {settings.verify_token}")
    print("=" * 60)
    print("\n  ➡️  Go to Meta Developer Console:")
    print("     https://developers.facebook.com/apps/")
    print(f"     Set Callback URL to: {public_url}/webhook")
    print(f"     Set Verify Token to: {settings.verify_token}")
    print("\n  Press Ctrl+C to stop the tunnel\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Shutting down ngrok tunnel...")
        ngrok.kill()


if __name__ == "__main__":
    start_tunnel()
