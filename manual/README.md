# Manual integration demos

These scripts exercise real browsers, providers, or MCP services. They are kept outside `tests/` because they require credentials, external services, interactive sessions, or human input and are not deterministic regression tests.

Run a demo from the repository root with `python manual/<script-name>.py`. Configure the environment variables used by that demo first. The scripts are exploratory examples and may open browser windows or make provider requests.
