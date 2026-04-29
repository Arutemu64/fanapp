When writing backend tests follow these rules:

- Check out existing tests as an example
- Prefer resolving dependencies through `dishka_request` container fixture
- Implement in-memory fakes/stubs to mock external dependencies