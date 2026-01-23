import json

# Dictionary to store messages with auto-incrementing IDs
messages = {}
_next_id = 1

def create_message(data: str) -> str:
    """Uses the data in this parameter to make gmail
    messages based off of the gmail api found in the
    google developers page. Adds this to the messages
    dictionary with a respective key value that is
    iterated. This key value is the ID used to retrieve
    created emails later.

    Args:
        data: Some JSON encoding of data used to
        fill the gmail message with info

    Returns:
        The key value which is the email ID as a string
    """
    global _next_id

    # Parse the JSON data
    message_data = json.loads(data)

    # Generate ID and store message
    message_id = str(_next_id)
    messages[message_id] = message_data
    _next_id += 1

    return message_id

def get_message(message_id: str) -> str:
    """Gets the email message associated with the
    parameterized message_id string that is passed
    in.

    Args:
        message_id: A key value that is used to index
        the dictionary of messages

    Returns:
        The message indexed in the dictionary by
        'message_id'
    """
    if message_id in messages:
        return json.dumps(messages[message_id])
    else:
        raise KeyError(f"Message ID '{message_id}' not found")
    
def create_thread(data: list) -> str:
    """Uses the data in this parameter to combine all the 
    messages associated with the list of message_id's 
    into a "email thread."

    Args:
        data: a 
    """

def get_thread(thread_id: str) -> list:
    """
    """
