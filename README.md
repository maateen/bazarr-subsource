# Bazarr SubSource Integration

[![CI](https://github.com/maateen/bazarr-subsource/actions/workflows/ci.yml/badge.svg)](https://github.com/maateen/bazarr-subsource/actions/workflows/ci.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> ⚠️ **Active Development**: This project is under active development. Features may change and stability is not guaranteed. Use at your own risk.

A Python automation tool that connects to your Bazarr instance, identifies movies and TV episodes missing subtitles, and automatically downloads them from SubSource.

## Features

- 🎬 **Automatic Movie Detection**: Lists all movies missing subtitles from your Bazarr instance
- 📺 **TV Show Episode Support**: Automatically downloads subtitles for wanted TV show episodes
- 🌐 **SubSource Integration**: Downloads subtitles from SubSource's anonymous API (no account needed)
- 📤 **Seamless Upload**: Automatically uploads downloaded subtitles back to Bazarr
- 🌍 **Multi-language Support**: Supports multiple languages, forced, and hearing impaired subtitles
- ⏱️ **Smart Retry Logic**: Uses Bazarr's own search intervals to avoid redundant API calls
- 📊 **Progress Tracking**: Tracks search history to prevent unnecessary duplicate searches
- 🧹 **Clean Operation**: Automatically cleans up temporary files after successful uploads
- ⚙️ **Configurable**: External configuration file for easy setup
- 🔧 **Episode Matching**: Intelligent episode matching using season/episode patterns and scene names

## Requirements

- Python 3.13+
- Bazarr instance with API access
- Internet connection for SubSource API (no account required)
- Basic authentication credentials (only if using reverse proxy with auth in front of Bazarr)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/maateen/bazarr-subsource.git
   cd bazarr-subsource
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the script** (it will create a default config file):
   ```bash
   python run.py
   ```

4. **Edit the configuration file** at `~/.config/bazarr-subsource/config.cfg`:
   ```ini
   [bazarr]
   url = https://yourbazarr.example.com
   api_key = your_api_key_here

   [auth]
   # Only needed if you have a reverse proxy with basic auth in front of Bazarr
   # Leave empty or remove this section if connecting directly to Bazarr
   username = your_username
   password = your_password

   [subsource]
   api_url = https://api.subsource.net/v1

   [download]
   directory = /tmp/downloaded_subtitles

   [movies]
   # Enable movie subtitle downloads
   enabled = true

   [episodes]
   # Enable TV show episode subtitle downloads
   enabled = true
   # Search patterns: season_episode,episode_title,scene_name
   search_patterns = season_episode,episode_title,scene_name

   [logging]
   level = INFO
   file = /var/log/bazarr_subsource.log
   ```

5. **Run again** to start downloading subtitles:
   ```bash
   python run.py
   ```

## Automated Execution with Cron

This tool is designed to run automatically via cron for continuous subtitle monitoring.

### Setting up Cron Job

1. **Find your Python path**:
   ```bash
   which python3
   # Output: /usr/bin/python3 (or your specific path)
   ```

2. **Get the full script path**:
   ```bash
   pwd
   # Note the full path to your bazarr-subsource directory
   ```

3. **Edit your crontab**:
   ```bash
   crontab -e
   ```

4. **Add cron job examples**:
   ```bash
   # Run every 6 hours
   0 */6 * * * /usr/bin/python3 /home/user/bazarr-subsource/run.py >> /home/user/bazarr-subsource/cron.log 2>&1

   # Run daily at 3 AM
   0 3 * * * /usr/bin/python3 /home/user/bazarr-subsource/run.py >> /home/user/bazarr-subsource/cron.log 2>&1

   # Run twice daily (6 AM and 6 PM)
   0 6,18 * * * /usr/bin/python3 /home/user/bazarr-subsource/run.py >> /home/user/bazarr-subsource/cron.log 2>&1
   ```

### Cron Best Practices

- **Use absolute paths** for both Python and script locations
- **Redirect output** to log files for debugging (`>> logfile 2>&1`)
- **Set appropriate frequency** - respect API rate limits
- **Monitor logs** regularly for issues
- **Use virtual environment** if needed:
  ```bash
  0 */6 * * * /home/user/bazarr-subsource/venv/bin/python /home/user/bazarr-subsource/run.py >> /home/user/bazarr-subsource/cron.log 2>&1
  ```

### Recommended Cron Intervals

- **Conservative**: Every 12-24 hours
- **Moderate**: Every 6-8 hours
- **Aggressive**: Every 2-4 hours (monitor API limits)

The tool's built-in tracking system prevents redundant searches, making frequent runs safe.

## Configuration

### Bazarr Settings
- `url`: Your Bazarr instance URL
- `api_key`: Your Bazarr API key (found in Settings → General)

### Authentication
- `username` & `password`: Basic auth credentials (only needed if you have a reverse proxy with authentication in front of Bazarr)

### SubSource Settings
- `api_url`: SubSource API endpoint (default: `https://api.subsource.net/v1`)
- **Note**: No SubSource account or authentication required - uses anonymous API access

### Download Settings
- `directory`: Local directory for temporary subtitle files (default: `/tmp/downloaded_subtitles`)

### Movies Settings
- `enabled`: Enable movie subtitle downloads (default: `true`)

### Episodes Settings
- `enabled`: Enable TV show episode subtitle downloads (default: `true`)
- `search_patterns`: Episode search patterns, comma-separated (default: `season_episode,episode_title,scene_name`)
  - `season_episode`: Search using "Series S01E01" format
  - `episode_title`: Search using "Series Episode Title" format
  - `scene_name`: Search using scene release names

### Logging
- `level`: Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `file`: Log file path (default: `/var/log/bazarr_subsource.log`)
- Log rotation: 10MB max file size, keeps 5 backup files

## How It Works

### Movies
1. **Connect to Bazarr**: Fetches all movies missing subtitles using the `/api/movies/wanted` endpoint
2. **Search SubSource**: For each movie, searches SubSource API for available subtitles
3. **Smart Filtering**: Uses Bazarr's own search intervals to avoid redundant searches
4. **Download Process**: Downloads subtitle ZIP files and extracts the subtitle files
5. **Upload to Bazarr**: Uploads extracted subtitles back to Bazarr using the `/api/movies/subtitles` endpoint
6. **Cleanup**: Removes temporary files and updates tracking data

### TV Show Episodes
1. **Connect to Bazarr**: Fetches all episodes missing subtitles using the `/api/episodes/wanted` endpoint
2. **Episode Enrichment**: Retrieves series information for each episode from `/api/series`
3. **Multi-Pattern Search**: Searches SubSource using various patterns:
   - Series name + S01E01 format
   - Series name + episode title
   - Scene release names
4. **Episode Matching**: Filters SubSource results to match specific season/episode using regex patterns
5. **Upload to Bazarr**: Uploads matched subtitles using the `/api/episodes/subtitles` endpoint
6. **Cleanup**: Removes temporary files and updates episode tracking data

## Advanced Features

### Intelligent Retry Logic
The tool integrates with Bazarr's system tasks to determine optimal search intervals:
- Reads Bazarr's "Search for Missing Movies Subtitles" task interval
- Prevents redundant searches within the configured timeframe
- Maintains a local tracking database at `~/.config/bazarr-subsource/tracking.json`

### Movie Year Detection
- Automatically detects movie years from Bazarr's search API
- Improves SubSource search accuracy
- Handles various year field formats from different sources

### Error Handling
- Comprehensive error logging and debugging information
- Graceful handling of network issues and API limitations
- Rate limiting to respect SubSource API constraints

## Development

### Setup Development Environment

1. **Install development dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

4. **Run pre-commit checks**:
   ```bash
   pre-commit run --all-files
   ```

### Code Quality
This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **pytest** for unit testing with coverage reporting
- **pre-commit** hooks for automated checks

### Testing
Run the test suite with coverage:
```bash
pytest --cov=. --cov-report=html
```

Individual test modules:
```bash
pytest tests/core/test_config.py -v
pytest tests/api/test_bazarr.py -v
```

### Project Structure
```
bazarr-subsource/
├── run.py              # Main entry point
├── api/                # API clients
│   ├── __init__.py
│   ├── bazarr.py       # Bazarr API client
│   └── subsource.py    # SubSource API client
├── core/               # Core functionality
│   ├── __init__.py
│   ├── config.py       # Configuration management
│   └── tracking.py     # Search tracking system
├── tests/              # Unit tests
│   ├── __init__.py
│   ├── api/            # API module tests
│   ├── core/           # Core module tests
│   ├── test_utils.py   # Utils tests
│   └── test_run.py     # Main module tests
├── utils.py            # Utility functions
├── requirements.txt    # Python dependencies
├── requirements-dev.txt # Development dependencies
├── pytest.ini         # Test configuration
├── .pre-commit-config.yaml
├── .gitignore
└── .github/            # GitHub templates & workflows
    ├── workflows/
    │   └── ci.yml
    └── ISSUE_TEMPLATE/
```

## API Rate Limits

SubSource's anonymous API has rate limits. This tool implements:
- 2-second delays between API calls
- Intelligent retry logic based on Bazarr's intervals for both movies and episodes
- Local tracking to minimize unnecessary requests
- Episode-specific search patterns to reduce API calls
- No authentication headers or account credentials needed

## Troubleshooting

### Common Issues

**"No movies are currently missing subtitles!" / "No episodes want subtitles."**
- Check if your Bazarr has movies/episodes with missing subtitles
- Verify your Bazarr API key and URL are correct
- For episodes: Ensure `episodes_enabled = true` in your config

**"Error connecting to Bazarr API"**
- Ensure Bazarr is running and accessible
- Check your network connection and firewall settings
- Verify basic auth credentials if you're using a reverse proxy with authentication

**"429 Client Error" from SubSource**
- The tool includes rate limiting, but if you encounter this:
- Wait a few minutes before retrying
- Check if you're running multiple instances

**Configuration file not found**
- The tool creates a default config on first run
- Edit `~/.config/bazarr-subsource/config.cfg` with your settings

**Episode subtitles not found**
- Episodes are searched using multiple patterns (S01E01, episode title, scene name)
- SubSource has limited TV show coverage compared to movies
- Check if the series name matches exactly in both Bazarr and SubSource
- Some episodes may not have subtitles available on SubSource

**Cron job not running or failing**
- Check cron service is running: `sudo systemctl status cron`
- Verify cron job syntax: `crontab -l`
- Check cron logs: `tail -f /var/log/cron` or `journalctl -f -u cron`
- Ensure absolute paths are used in crontab
- Check file permissions on script and config files
- Test the command manually first before adding to cron

**Script works manually but fails in cron**
- Environment variables may be different in cron
- Add PATH to your crontab: `PATH=/usr/local/bin:/usr/bin:/bin`
- Use absolute paths for all commands and files
- Redirect both stdout and stderr: `>> /path/to/logfile 2>&1`

## Development Status

This project is in **active development**:
- Features are being added and refined
- Breaking changes may occur
- Direct commits to `main` branch during development phase
- No versioned releases until the project reaches stability
- Community feedback and contributions are welcome

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and ensure tests pass
4. Run pre-commit checks: `pre-commit run --all-files`
5. Commit your changes: `git commit -m "Add feature"`
6. Push to your fork: `git push origin feature-name`
7. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use only. Please respect SubSource's terms of service and API usage guidelines. The authors are not responsible for any misuse of this tool.

## Support

If you encounter issues:
1. Check the [troubleshooting section](#troubleshooting)
2. Review the log files for detailed error information
3. Create an issue on GitHub with:
   - Your configuration (remove sensitive data)
   - Log output showing the error
   - Steps to reproduce the issue

## AI-Generated Code Policy

Part of this codebase was generated or written with AI assistance but has been thoroughly reviewed by humans. While AI-generated code contributions are permitted, all code must be reviewed by humans before merging to the main branch.

## Acknowledgments

- [Bazarr](https://www.bazarr.media/) - Subtitle management for Sonarr and Radarr
- [SubSource](https://subsource.net/) - Subtitle database and API
- Python community for excellent libraries used in this project
- AI assistance in code generation with human oversight and review
