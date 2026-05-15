# Using the Browser Agent with curl

The simple browser agent endpoint provides a REST API that you can interact with using curl.

## Quick Examples

### Method 1: One-liner (Simple but waits for completion)

```bash
# Submit task and wait for result
EVENT_ID=$(curl -s -X POST 'http://127.0.0.1:7789/gradio_api/call/predict' \
  -H 'Content-Type: application/json' \
  -d '{"data":["Go to example.com and get the page title"]}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['event_id'])")

echo "Event ID: $EVENT_ID"

# Wait a bit for the agent to complete (adjust time based on task complexity)
sleep 30

# Get the result
curl -s -N "http://127.0.0.1:7789/gradio_api/call/predict/${EVENT_ID}" | \
  grep 'process_completed' | \
  sed 's/^data: //' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['output']['data'][0])"
```

### Method 2: Using the provided script

```bash
# Use the ready-made script
./curl_simple.sh "Your task here"

# Examples:
./curl_simple.sh "Go to wikipedia.org and search for 'artificial intelligence'"
./curl_simple.sh "Navigate to google.com and tell me what you see"
```

## API Details

### Endpoint: `/gradio_api/call/predict`

**Base URL:** `http://127.0.0.1:7789`

### Step 1: Submit a Task

**Request:**
```bash
POST /gradio_api/call/predict
Content-Type: application/json

{
  "data": ["Your task description here"]
}
```

**Example:**
```bash
curl -X POST 'http://127.0.0.1:7789/gradio_api/call/predict' \
  -H 'Content-Type: application/json' \
  -d '{"data":["Go to example.com and tell me the page title"]}'
```

**Response:**
```json
{
  "event_id": "e29f3556d3754156ad7ed239780db6e8"
}
```

### Step 2: Get the Result

**Request:**
```bash
GET /gradio_api/call/predict/{event_id}
```

**Example:**
```bash
curl -N 'http://127.0.0.1:7789/gradio_api/call/predict/e29f3556d3754156ad7ed239780db6e8'
```

**Response Stream:**
The endpoint returns Server-Sent Events (SSE). Look for the `process_completed` event:

```
event: generating
data: {"msg":"process_generating",...}

event: complete
data: {"msg":"process_completed","output":{"data":["The page title is: Example Domain"]},...}
```

## Advanced: Complete curl Example

```bash
#!/bin/bash

# Configuration
API_URL="http://127.0.0.1:7789/gradio_api"
TASK="Go to example.com and get the page title"

# Submit task
echo "Submitting task: $TASK"
RESPONSE=$(curl -s -X POST "${API_URL}/call/predict" \
  -H "Content-Type: application/json" \
  -d "{\"data\":[\"${TASK}\"]}")

EVENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['event_id'])")
echo "Event ID: $EVENT_ID"

# Poll for result (adjust sleep time based on task complexity)
echo "Waiting for completion..."
for i in {1..60}; do
  RESULT=$(curl -s -N "${API_URL}/call/predict/${EVENT_ID}" 2>/dev/null | \
    grep -m 1 'process_completed' | \
    sed 's/^data: //')

  if [ ! -z "$RESULT" ]; then
    echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['output']['data'][0])"
    exit 0
  fi

  echo -n "."
  sleep 2
done

echo "\nTimeout"
```

## Task Examples

```bash
# Web navigation
"Go to github.com and find the trending repositories"

# Information extraction
"Visit weather.com and tell me the temperature in San Francisco"

# Web search
"Go to google.com and search for 'machine learning tutorials'"

# Form interaction
"Navigate to example.com/contact and fill out the contact form"
```

## Model Configuration

The simple agent uses these defaults:
- **Model:** claude-sonnet-4-5-20250929 (Anthropic)
- **Temperature:** 0.6
- **Max Steps:** 100
- **Max Actions per Step:** 10
- **Vision:** Enabled
- **Browser:** Headless mode

The API key is read from the `ANTHROPIC_API_KEY` environment variable.

## Tips

1. **Task Complexity:** Simple tasks (viewing a page) complete in ~10-30 seconds. Complex tasks (form filling, searches) may take 1-3 minutes.

2. **Timeout:** Set appropriate timeouts based on your task. The script defaults to 5 minutes.

3. **Error Handling:** Check for errors in the response:
```bash
if echo "$RESPONSE" | grep -q "Error:"; then
  echo "Task failed"
fi
```

4. **Multiple Requests:** Each task creates a new browser session, so requests are independent.
