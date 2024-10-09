import asyncio
import websockets
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import in_terminal
from prompt_toolkit.widgets import Frame
from datetime import datetime
import json
import textwrap
from prompt_toolkit.output import create_output

from psky import login, create_post_with_facets

class ChatClient:
    def __init__(self, websocket_url, username, password):
        self.websocket_url = websocket_url
        self.username = username
        self.password = password
        self.session = None
        self.messages = []
        self.input_buffer = Buffer()
        self.output_control = FormattedTextControl(text="")
        self.kb = KeyBindings()
        self.application = None
        self.char_count_control = FormattedTextControl(text="Characters: 0/256")
        self.max_width = 80  # Default max width
        self.output_height = 20  # Default output height
        self.update_terminal_size()

        @self.kb.add('c-c')
        def _(event):
            event.app.exit()

        @self.kb.add('enter')
        def _(event):
            if self.input_buffer.text:
                asyncio.create_task(self.send_message(self.input_buffer.text))
                self.input_buffer.reset()
                self.update_char_count(self.input_buffer)  # Reset character count

    def update_terminal_size(self):
        output = create_output()
        terminal_size = output.get_size()
        self.max_width = max(80, min(terminal_size.columns - 2, 120))  # Min 80, max 120
        self.output_height = terminal_size.rows - 5  # Subtract space for input and char count

    async def login_to_bluesky(self):
        try:
            self.session = login(self.username, self.password)
            self.add_message("System", "Logged in to Bluesky successfully")
        except Exception as e:
            self.add_message("Error", f"Failed to log in to Bluesky: {str(e)}")

    async def update_messages(self):
        while True:
            try:
                self.add_message("System", "Connecting to WebSocket...")
                async with websockets.connect(self.websocket_url) as websocket:
                    self.add_message("System", "Connected to WebSocket")
                    while True:
                        message = await websocket.recv()
                        self.add_message("Received", message)
            except websockets.exceptions.WebSocketException:
                self.add_message("System", "WebSocket connection closed. Reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                self.add_message("Error", f"WebSocket error: {str(e)}")
                await asyncio.sleep(5)

    async def send_message(self, message):
        if not self.session:
            self.add_message("Error", "Not logged in to Bluesky. Cannot send message.")
            return

        try:
            result = create_post_with_facets(self.session, message)
            # self.add_message("Sent", message)
            self.update_char_count(self.input_buffer)  # Reset character count
        except ValueError as e:
            self.add_message("Error", f"Failed to send: {str(e)}")
        except Exception as e:
            self.add_message("Error", f"Failed to send: {str(e)}")

    def add_message(self, prefix, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if prefix == "Received":
            try:
                data = json.loads(message)
                if data["$type"] == "social.psky.feed.post#create":
                    nickname = data.get("nickname")
                    handle = data.get("handle", "unknown")
                    post = data.get("post", "")
                    if nickname:
                        header = f"[{timestamp}] {nickname} [@{handle}]: "
                    else:
                        header = f"[{timestamp}] @{handle}: "

                    # Calculate remaining width for the post content
                    remaining_width = self.max_width - len(header)

                    # Wrap the post content
                    wrapped_lines = textwrap.wrap(post, width=remaining_width, break_long_words=False, break_on_hyphens=False)

                    # Combine header with the first line of the wrapped post
                    formatted_message = header + wrapped_lines[0]

                    # Add remaining lines with proper indentation
                    if len(wrapped_lines) > 1:
                        indent = " " * len(header)
                        formatted_message += "\n" + "\n".join(indent + line.lstrip() for line in wrapped_lines[1:])
                else:
                    formatted_message = f"[{timestamp}] {prefix}: Unsupported message type"
            except json.JSONDecodeError:
                formatted_message = f"[{timestamp}] {prefix}: Invalid JSON: {message}"
            except KeyError:
                formatted_message = f"[{timestamp}] {prefix}: Unexpected data format: {message}"
        else:
            formatted_message = f"[{timestamp}] {prefix}: {message}"
            # Wrap system messages if they're too long
            if len(formatted_message) > self.max_width:
                wrapped_lines = textwrap.wrap(formatted_message, width=self.max_width, break_long_words=False, break_on_hyphens=False)
                formatted_message = "\n".join(wrapped_lines)

        self.messages.append(formatted_message)
        self.update_output()

    def update_output(self):
        # Join messages and split into lines
        all_lines = "\n".join(self.messages).split("\n")

        # Take only the last lines that fit in the output window
        visible_lines = all_lines[-self.output_height:]

        self.output_control.text = "\n".join(visible_lines)
        if self.application:
            self.application.invalidate()

    def update_char_count(self, buffer):
        count = len(buffer.text)
        self.char_count_control.text = f"Characters: {count}/256"
        if self.application:
            self.application.invalidate()

    async def run_async(self):
        await self.login_to_bluesky()

        output_window = Frame(
            Window(content=self.output_control),
            title="Messages"
        )

        char_count_window = Window(content=self.char_count_control, height=1, align="right")

        input_window = Frame(
            Window(height=3, content=BufferControl(buffer=self.input_buffer)),
            title="Input"
        )

        layout = Layout(
            HSplit([
                output_window,
                char_count_window,
                input_window,
            ])
        )

        self.application = Application(
            layout=layout,
            key_bindings=self.kb,
            full_screen=True,
        )

        self.input_buffer.on_text_changed += self.update_char_count

        async with in_terminal():
            # Update terminal size before running the application
            self.update_terminal_size()

            background_task = asyncio.create_task(self.update_messages())
            await self.application.run_async()
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass

    def run(self):
        asyncio.run(self.run_async())

if __name__ == "__main__":
    websocket_url = "wss://pico.api.bsky.mom/subscribe"  # WebSocket URL for psky API
    username = "" # your bluesky handle
    password = "" # your bluesky app password (not your login password)
    # See https://bsky.app/settings/app-passwords
    client = ChatClient(websocket_url, username, password)
    client.run()