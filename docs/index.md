# VObjectX

A full-featured Python3 package for parsing and creating iCalendar and vCard files.

## Overview

VObjectX is a comprehensive library for working with calendar and contact data in Python. It provides tools for:

- **iCalendar (RFC 5545)**: Parse and create `.ics` files for calendar data
- **vCard (RFC 6350)**: Parse and create `.vcf` files for contact information
- **hCalendar**: Microformat calendar data
- **Timezone handling**: Convert between timezones with proper DST handling

## Installation

```bash
pip install vobjectx
```

## Quick Start

### Working with iCalendar

```python
from vobjectx import icalendar

# Parse an ICS file
with open('calendar.ics', 'r') as f:
    cal = icalendar.read_one(f.read())
    
# Access calendar properties
print(cal.summary.value)
print(cal.dtstart.value)
```

### Working with vCards

```python
from vobjectx import vcard

# Parse a VCF file
with open('contact.vcf', 'r') as f:
    card = vcard.read_one(f.read())
    
# Access contact information
print(card.n.value)
print(card.email.value)
```

## Features

- Full support for iCalendar (RFC 5545) components
- vCard 3.0 and 4.0 support
- Timezone-aware date handling
- Command-line tools for diff and timezone conversion
- Extensible architecture for custom components

## Command-Line Tools

VObjectX includes two command-line utilities:

- **`ics_diff`**: Compare two ICS files and show differences
- **`change_tz`**: Convert calendar events between timezones

## Documentation

- [API Reference](api/index.md) - Complete API documentation
- [GitHub Repository](https://github.com/rsb-23/vobjectx) - Source code and issues

## License

Apache License 2.0 - See [LICENSE](https://github.com/rsb-23/vobjectx/blob/main/LICENSE) for details.
