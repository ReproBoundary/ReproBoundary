# How execution logs are cleaned

**Redaction** means replacing sensitive text before a file is released. The
released execution logs are generated automatically from the protected archive.

The cleaning program replaces detected:

- private home and shared-storage paths;
- login information sent in request headers and browser cookies;
- recognized keys or tokens used to access online services;
- variables that appear to store credentials;
- JSON Web Tokens, which are signed strings often used for login;
- secret values placed in a URL; and
- private-key blocks.

The program does not otherwise rewrite scientific statements or tool output.
If a sensitive pattern appears inside scientific output, that matching text is
still replaced.

For each run, the index records the number of replacements and SHA-256 hashes
for both the protected and released log. SHA-256 is a method for creating a
digital fingerprint of a file.

## Files not released

The public package does not include raw machine security records or raw
requests and responses exchanged with online services. These files may contain
private machine or service-provider information.

## Required checks before publication

Download the fixed Hugging Face trajectory dataset and run from its root:

```bash
python3 scripts/verify_dataset.py
```

The GitHub code release contains only the trajectory index, not the compressed
logs. Also inspect a sample of dataset logs with many replacements. Automatic
matching can miss a sensitive value that uses an unexpected format. A
replacement count of zero means only that no configured pattern matched; it
does not prove that the log contains no sensitive information.
