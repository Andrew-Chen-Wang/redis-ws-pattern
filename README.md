# Testing Redis pattern matching

Ensuring that each FastAPI application only creates a single Redis connection.

### How does this work?

We're essentially making a single Redis connection for each FastAPI application.
Every time a user connects, we create a new `asyncio.Task`. Everytime our Redis
PubSub connection receives a message for "channel:*" wildcard, we find a task
that matches that ID and run the task.

### QA Steps

1. Start two FastAPI applications:
  `uvicorn main:app --reload --port 8000` and `uvicorn main:app --reload --port 8001`
2. Open your browser and go to:

- http://localhost:8000/1
- http://localhost:8001/1
- http://localhost:8001/1
- http://localhost:8000/2
- http://localhost:8001/2

When sending messages, we're looking to ensure there isn't cross pollution of
messages between the two websockets. This is ensured via the wildcard pattern
matching that occurs and immediately filtered.

To check, `redis-cli` then run `client list`. You should only have three connections.

### License and Contribution

```
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by a[README.md](README.md)pplicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
