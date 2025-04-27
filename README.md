# pymbrewclient

`pymbrewclient` is a Python library and CLI tool for interacting with Minibrew's API. It provides both programmatic access and a command-line interface for fetching brewery and session information.

---

## Features

- Fetch brewery overview data.
- Retrieve session information.
- Easy-to-use CLI for quick access.
- Python library for programmatic integration.

---

### PLEASE NOTE
This library will only work with a valid subscription to the pro portal.

## Installation

You can install `pymbrewclient` using `pip`:

### CLI

```bash
pip install pymbrewclient
```

```bash
pymbrewclient get-token --username <USERNAME> --password <PASSWORD>
```

```bash
pymbrewclient brewery-overview
```

```bash
pymbrewclient session-info --username <USERNAME> --password <PASSWORD> --session-id <SESSION_ID>
```

### Library Usage

```python
from pymbrewclient import pymbrewclient

# Initialize the client
client = pymbrewclient(username,password)

# Fetch brewery overview
brewery_overview = client.get_brewery_overview()
print(brewery_overview)
```

```python
from pymbrewclient import pymbrewclient

# Initialize the client
client = pymbrewclient()

# Fetch session info
session_id = 12345
session_info = client.get_session_info(session_id)
print(session_info)
```


## Development

Clone the repository:
```
git clone https://github.com/yourusername/pymbrewclient.git
cd pymbrewclient
```

Install dependencies:
```
pip install .[dev]
```

Run tests:
```
pytest
```

Lint the code:
```
make lint
```