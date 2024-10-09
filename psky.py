import requests
import re

# Bluesky API endpoints
BASE_URL = "https://bsky.social/xrpc"
LOGIN_URL = f"{BASE_URL}/com.atproto.server.createSession"
CREATE_RECORD_URL = f"{BASE_URL}/com.atproto.repo.createRecord"

psky_lexicon = {
    "lexicon": 1,
    "id": "social.psky.feed.post",
    "defs": {
        "main": {
            "type": "record",
            "description": "A Picosky post containing at most 64 graphemes.",
            "key": "tid",
            "record": {
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {
                        "type": "string",
                        "maxLength": 1000,
                        "maxGraphemes": 256,
                        "description": "Text content."
                    },
                    "facets": {
                        "type": "array",
                        "description": "Annotations of text (mentions, URLs, hashtags, etc)",
                        "items": {"type": "ref", "ref": "social.psky.richtext.facet"}
                    }
                }
            }
        }
    }
}

def login(username, password):
    response = requests.post(LOGIN_URL, json={"identifier": username, "password": password})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Login failed: {response.text}")

def publish_custom_record(session, text, facets=None):
    headers = {
        "Authorization": f"Bearer {session['accessJwt']}",
        "Content-Type": "application/json"
    }

    record = {
        "text": text,
    }

    if facets:
        record["facets"] = facets

    data = {
        "repo": session["did"],
        "collection": psky_lexicon["id"],
        "record": record
    }

    response = requests.post(CREATE_RECORD_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to publish record: {response.text}")

def create_facet(text, start, end, feature_type, feature_value):
    """
    Create a facet object based on the social.psky.richtext.facet lexicon.

    :param text: The full text of the post
    :param start: Start index of the feature in the text
    :param end: End index of the feature in the text
    :param feature_type: Type of feature ('mention', 'link', or 'room')
    :param feature_value: Value for the feature (DID for mention, URI for link, room name for room)
    :return: A facet object
    """
    byte_start = len(text[:start].encode('utf-8'))
    byte_end = len(text[:end].encode('utf-8'))

    facet = {
        "index": {
            "byteStart": byte_start,
            "byteEnd": byte_end
        },
        "features": []
    }

    if feature_type == 'mention':
        facet["features"].append({
            "$type": "social.psky.richtext.facet#mention",
            "did": feature_value
        })
    elif feature_type == 'link':
        facet["features"].append({
            "$type": "social.psky.richtext.facet#link",
            "uri": feature_value
        })
    elif feature_type == 'room':
        facet["features"].append({
            "$type": "social.psky.richtext.facet#room",
            "room": feature_value
        })

    return facet

def create_post_with_facets(session, text):
    """
    Create a new post with a custom message, automatically generating facets for mentions, links, and rooms.

    :param session: The session object obtained from login
    :param text: The text content of the post
    :return: The result of publishing the record
    """
    # Ensure the text doesn't exceed 256 graphemes
    if len(text) > 256:
        raise ValueError("Text exceeds 256 graphemes limit")

    facets = []

    # Find mentions
    mentions = re.finditer(r'@(\w+)', text)
    for match in mentions:
        start, end = match.span()
        # Note: In a real-world scenario, you'd need to resolve the handle to a DID
        facets.append(create_facet(text, start, end, 'mention', f'did:plc:{match.group(1)}'))

    # Find links
    links = re.finditer(r'(https?://\S+)', text)
    for match in links:
        start, end = match.span()
        facets.append(create_facet(text, start, end, 'link', match.group(1)))

    # Find rooms (hashtags)
    rooms = re.finditer(r'#(\w+)', text)
    for match in rooms:
        start, end = match.span()
        facets.append(create_facet(text, start, end, 'room', match.group(1)))

    # Publish the record with the generated facets
    return publish_custom_record(session, text, facets)