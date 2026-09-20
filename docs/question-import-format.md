# Question import format

Uploads may be UTF-8 `.txt`/`.md`, `.docx`, or text-based `.pdf` files up to 5 MB. All formats must contain the same plain-text markers.

## Valid example

```text
QUESTION: Which protocol secures HTTP?
OPTION: FTP
OPTION: TLS
OPTION: SMTP
OPTION: DNS
ANSWER: 2
EXPLANATION: TLS supplies encryption and authentication.
Further explanation lines may continue without a label.
---
QUESTION: Which number is prime?
OPTION: 4
OPTION: 6
OPTION: 7
OPTION: 8
OPTION: 9
ANSWER: 3
```

Rules:

- Start every record with `QUESTION:`.
- Include at least four `OPTION:` lines; additional options are supported.
- Include exactly one `ANSWER:` containing the one-based number of the correct option.
- `EXPLANATION:` is optional and may continue on subsequent lines.
- Separate records with `---` or start the next `QUESTION:` directly.
- Labels are case-insensitive; content remains Unicode.

## Invalid examples

This has fewer than four options:

```text
QUESTION: Invalid
OPTION: One
OPTION: Two
ANSWER: 1
```

This answer is out of range:

```text
QUESTION: Invalid
OPTION: One
OPTION: Two
OPTION: Three
OPTION: Four
ANSWER: 5
```

The preview reports errors with source line numbers and creates nothing until a staff member confirms a completely valid preview. A preview is stored server-side in the authenticated session rather than trusted from browser fields.

Scanned/image-only PDFs are rejected because version 1 does not perform OCR. Run OCR externally, confirm the resulting text, and upload the text-based PDF or normalized TXT file.
