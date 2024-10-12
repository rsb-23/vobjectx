Roadmap
=======

Immediate tasks, starting early 2024

- [x] Release 0.9.7 with new web links, suitable acks, etc.
- [x] Change to use GitHub Actions for CI (replacing TravisCI)
- [x] Decide on Python version support policy
  - Can we stop support for Python 2.7?
  - How early in 3.x do we need to support?
  - What's the policy for the future?
- [ ] Apply all open good PRs
  - Add unit test coverage where missing
  - Add comments to _eventable_ repo, so people can see they're being 
    fixed in the _py-vobject_ project
- [ ] Do a pass through the open issues at _eventable_
  - Fix anything easy
  - Copy the issue over to _py-vobject_ for bigger items that can't be
    fixed right away
- [ ] Make a new 0.9.x release (0.9.8?)
  - Include all applied PRs
  - Include all easy bug fixes
- [ ] Publish 0.9.x release to PyPI
  - Ideally, under existing `vobject` name
  - If that's not easy, try the new PyPI abandoned projects process
  - If that doesn't work, choose a new name as a last resort
- [ ] Make maintenance branch for 0.9.x
- [ ] Renumber _master_ for 1.0.x
  - And rename to `main` while we're here? 
- [ ] Set up GitHub issue triage, etc
  - Group members and permissions
  - Labels
  - Templates
  - Pinned discussions posts
  - Revamped README
  - CoC?
- [ ] Talk to downstream users about pain-points
  - Beyond just lack of maintenance
  - eg. Radicale

### Bigger projects

These should be prioritised once the basic maintenance and revamping work
has been completed.

- [ ] Create new Sphinx-based programmer's guide document
  - Publish via readthedocs
  - Move example code out of README.md
  - Publish automagically via GitHub Actions
- [ ] If dropping Python 2.x, begin slow removal of 2.x code
  - In particular, clean up `bytes` vs `str` everywhere
  - Remove `six`
  - Remove various `import` compatibility hacks
- [ ] Robust 4.0 support
- [ ] Parsing performance
- [ ] Unit-test coverage
