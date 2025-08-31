# Security Policy

## Supported Versions

> ⚠️ **Note**: This project is under active development with no stable releases yet.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

We take the security of this project seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report a Security Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please send an email to maateen@outlook.com with the following information:

- Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

### What to Expect

- We will acknowledge receipt of your vulnerability report within 2 business days
- We will provide a more detailed response within 7 business days indicating the next steps in handling your report
- We will keep you informed of the progress towards a fix and full announcement
- We may ask for additional information or guidance

## Security Considerations

### Configuration Security

- **API Keys**: Store your Bazarr API key securely in the configuration file with appropriate file permissions (600)
- **Credentials**: Never commit credentials to version control
- **Configuration Location**: The default config location `~/.config/bazarr-subsource/` provides user-level isolation

### Network Security

- **HTTPS**: Always use HTTPS URLs for your Bazarr instance
- **Authentication**: Enable basic authentication on your Bazarr instance if exposed to untrusted networks
- **Rate Limiting**: The tool implements rate limiting to avoid overwhelming external APIs

### File Security

- **Temporary Files**: The tool creates temporary files in the configured download directory and cleans them up after use
- **File Permissions**: Ensure your download directory has appropriate permissions
- **ZIP Extraction**: The tool safely extracts ZIP files and validates file types

### Dependencies

- **Regular Updates**: Keep dependencies updated to receive security patches
- **Vulnerability Scanning**: Use `safety check` to scan for known vulnerabilities in dependencies
- **Minimal Dependencies**: This project uses minimal external dependencies to reduce attack surface

## Security Best Practices

When using this tool:

1. **Restrict Network Access**: Run on a trusted network or use VPN if accessing remote Bazarr instances
2. **Regular Updates**: Keep Python and all dependencies updated
3. **File Permissions**: Set restrictive permissions on configuration files
4. **Monitoring**: Monitor log files for unusual activity
5. **Backup**: Regularly backup your Bazarr configuration and subtitle files

## Security Features

- **Input Validation**: All user inputs and API responses are validated
- **Secure HTTP**: Uses secure HTTP sessions with proper timeout handling
- **Error Handling**: Sensitive information is not exposed in error messages
- **Logging**: Security-relevant events are logged without exposing credentials

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported versions
4. Release new versions as quickly as possible

We appreciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contributions.
