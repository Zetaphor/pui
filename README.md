# Bluesky Terminal Chat Client

This project is a TUI (Text User Interface) chat client for the Bluesky social network. It allows users to connect to Bluesky, view incoming messages, and send posts directly from the terminal.

![Screenshot of the TUI](https://github.com/Zetaphor/pui/blob/main/screenshot.png?raw=true)

## Requirements

- Python 3.7+
- pip (Python package manager)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/bluesky-terminal-chat.git
   cd bluesky-terminal-chat
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

5. When you're done using the application, you can deactivate the virtual environment:
   ```
   deactivate
   ```

## Created by Anthropic's Claude 3.5 Sonnet

This entire project was created by prompting Anthropic's Claude 3.5 Sonnet.

## Configuration

Before running the client, you need to set up your Bluesky credentials. Open `main.py` and locate the following lines at the bottom of the file and populate them with your Bluesky handle and [app password](https://bsky.app/settings/app-passwords):

```python
username = "" # your bluesky handle
password = "" # your bluesky app password (not your login password)
# See https://bsky.app/settings/app-passwords
client = ChatClient(websocket_url, username, password)
client.run()
```
