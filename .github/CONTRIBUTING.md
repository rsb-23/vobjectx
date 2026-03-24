Contributing to vObjectx
=======================

Welcome, and thanks for considering contributing to vObjectx!

**_This document is an incomplete draft_**

Contributions can take many forms, from coding major features, through triaging issues, writing documentation,
assisting users, etc, etc.  
You can, of course, just dive right in, but it's generally a good idea to open an issue
(if the contribution addresses a problem) or a discussion to discuss your plans first.  
This avoids duplicate effort, and builds the community of contributors.

In all interactions, contributors should be polite, kind, and respectful of others.  
Remember that not everyone lives in the same country, speaks English as their native language, or has the same level
of experience and confidence.

Python Code
-----------
vObjectx is licensed under the Apache 2.0 License, and any code or documentation can only be accepted under those
terms. You do _not_ need a formal statement of origin, and are not required to sign over your copyright.

- All new code should adhere to the PEP-8 conventions, with some exceptions.
- All new code should be covered by unit tests.
- All contributions must maintain the existing API's syntax and semantics, except major releases.

Dev Setup
-
1. Install dependencies
   ```
   pip install -e '.[lint]'
   ```
2. Enable pre-commit hook and run manually.
   ```
   pre-commit install
   git add . && pre-commit run
   ```
