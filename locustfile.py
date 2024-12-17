import json
import socketio
from locust import User, task, events
from locust.runners import MasterRunner
import time
import logging

logging.basicConfig(level=logging.INFO)

# A custom Locust User class for socket.io load testing
class SocketIOUser(User):
    abstract = True  # Prevent Locust from directly instantiating this class

    def __init__(self, environment):
        super().__init__(environment)
        self.client = socketio.SimpleClient()  # Create a SimpleClient instance
        self.url = "https://inquiry.lazyinwork.com/"  # Target WebSocket server

    def on_start(self):
        """Set up the WebSocket connection when a user starts"""
        try:
            self.client.connect(
                self.url, 
                socketio_path="s/socket.io/", 
                headers={"Content-Type": "application/json"},
                wait_timeout=5
            )
            logging.info("[CONNECTED] SocketIO Client connected.")
        except Exception as e:
            logging.error(f"[ERROR] Failed to connect: {e}")

    def on_stop(self):
        """Disconnect the WebSocket client when the user stops"""
        try:
            self.client.disconnect()
            logging.info("[DISCONNECTED] SocketIO Client disconnected.")
        except Exception as e:
            logging.error(f"[ERROR] Failed to disconnect: {e}")


class SocketIOHealthCheckUser(SocketIOUser):
    @task
    def health_check(self):
        """Send and validate the 'health-check' event"""
        try:
            # Prepare request body
            body = {
                "userId": "00001",
                "action": "test",
                "log": "200 GET \"something text\" 中文測試"
            }
            
            # Emit 'health-check' event
            start_time = time.time()
            self.client.emit("health-check", json.dumps(body))
            logging.info(f"[SENT] Sent health-check: {body}")
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logging.error(f"[ERROR] {e}")
            raise e

        try:
            # Wait for response
            response = self.client.receive(timeout=5)
            total_time = int((time.time() - start_time) * 1000)  # Response time in ms

            if response:
                event_name = response[0]
                payload = response[1]
                logging.info(f"[RECEIVED] Event: {event_name}, Data: {payload}")
                parsed_payload = json.loads(payload)

                
                # Validate response
                assert event_name == "re-health-check", "Event name mismatch!"
                assert parsed_payload["userBody"] == body, "Response payload mismatch!"

                events.request.fire(
                    request_type="socket.io",
                    name="health-check",
                    response_time=total_time,
                    response_length=len(str(response)),
                    exception=None
                )
            else:
                raise Exception("No response received from server!")
        except json.JSONDecodeError as e:
            logging.error(f"[ERROR] Failed to parse JSON: {e}")
            raise e


# Define the test configuration for Locust
class TestSocketIOBehavior(SocketIOHealthCheckUser):
    wait_time = lambda self: 1  # Time to wait between tasks


# Event listeners for Locust's master/slave setup
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    if isinstance(environment.runner, MasterRunner):
        logging.info("[INFO] Locust Master initialized")
    else:
        logging.info("[INFO] Locust Worker initialized")
