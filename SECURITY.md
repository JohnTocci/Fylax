# Security Policy

## Supported Versions

We actively support the following versions of Fylax with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The security of Fylax is important to us. If you discover a security vulnerability, please follow these steps:

### 1. Do Not Open a Public Issue

Please **do not** report security vulnerabilities through public GitHub issues. This helps protect users who haven't updated yet.

### 2. Contact Us Privately

Send a detailed report to: **john@johntocci.com**

Include the following information:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)
- Your contact information

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 1 week
- **Fix Timeline**: Varies based on severity

### 4. Disclosure Process

1. We'll acknowledge receipt of your report
2. We'll investigate and validate the vulnerability
3. We'll develop and test a fix
4. We'll release the fix and notify users
5. We'll publicly acknowledge your contribution (if desired)

## Security Considerations

### File System Safety

Fylax includes several built-in safety features:

- **Protected File Types**: System files (`.exe`, `.dll`, `.sys`) are never moved
- **Dangerous Path Detection**: Blocks organization of system directories
- **Hidden File Handling**: Respects system hidden file attributes
- **Path Validation**: Prevents path traversal and dangerous operations

### Configuration Security

- Configuration files are validated before use
- User input is sanitized to prevent injection attacks
- File paths are normalized and validated

### Best Practices for Users

1. **Run from trusted sources**: Only download Fylax from official repositories
2. **Review rules**: Always review organization rules before running
3. **Use dry-run**: Test organization with dry-run mode first
4. **Backup important data**: Create backups before large organization operations
5. **Keep updated**: Install security updates promptly

## Known Security Considerations

### File System Operations

Fylax performs file system operations that could potentially be misused:
- File moving and copying
- Directory creation
- File deletion (in duplicate handling)

**Mitigation**: Built-in safety checks and user confirmation for destructive operations.

### Configuration Files

The `config.json` file controls file organization behavior:
- Could be modified by malicious software
- Contains file path patterns

**Mitigation**: Input validation and path sanitization.

## Reporting Non-Security Issues

For non-security related bugs and issues, please use our [GitHub Issues](https://github.com/JohnTocci/Fylax/issues) page.

## Contact

For security-related inquiries:
- **Email**: john@johntocci.com
- **PGP Key**: Available upon request

Thank you for helping keep Fylax secure!