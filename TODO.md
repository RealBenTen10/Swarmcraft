## Big picture
- [ ] scaling tests
- [ ] foraging demo (or some kind of demo)

## Small bits
- [ ] logging
- [x] scale (mostly done via pooler)
- [x] programmatic environments
- [x] local communication

### Local communication
- communication on the server is rate-limited for anti-spam reasons
- spam filter is baked-in, can't be circumvented without a server plugin (but there are none for this on the sponge platform,
so we'd have to switch to forge which would complicate evocraft)
- the other option is a built in communication system which runs on the python side, could be handled by the pooler - just append right to the message queues
already given in sensing
- disadvantage is we lose feedback in the server

### Scaling
- server itself seems to handle large numbers of agents a-ok (no big surprise)
- the question is reusing agents - need an agent pool of agents which are not in use (initialized at start)
- also need an agent reset method
- then whenever we ask for a new agent, pull one out of the pool. if there are none left, create a new one, throw him in the pool, return
- agents will need an internal identifier, since usernames can't be changed at runtime
