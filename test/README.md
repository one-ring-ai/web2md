# Web2MD Token Usage Testing

This directory contains tools for testing and measuring token usage of web2md across different types of websites.

## Files

- `queries.txt` - Contains test queries divided into two categories:
  - Normal Web Search Queries (news, general info, etc.)
  - Documentation/Technical Queries (programming docs, tutorials, etc.)
- `token_usage_test.py` - Script that runs all queries and measures token usage
- `token_usage_results.json` - Generated results file with detailed statistics

## How to Run the Test

1. **Start web2md locally**:
   ```bash
   # Option 1: Using development environment
   cd dev
   ./run-services.sh
   # Then in another terminal:
   uvicorn main:app --host 0.0.0.0 --port 7001 --reload --env-file dev/.env
   
   # Option 2: Using Docker
   docker compose up -d
   ```

2. **Run the token usage test**:
   ```bash
   cd test
   python3 token_usage_test.py
   ```

3. **View results**:
   - Summary will be printed to the console
   - Detailed results saved to `token_usage_results.json`

## Configuration

You can modify the test parameters in `token_usage_test.py`:

- `WEB2MD_BASE_URL` - URL where web2md is running (default: http://localhost:7001)
- `NUM_RESULTS` - Number of search results to process per query (default: 3)
- `DELAY_BETWEEN_REQUESTS` - Seconds to wait between requests (default: 2)

## Understanding the Results

The test will provide:

- **Total tokens per category** - Sum of all tokens for normal vs documentation sites
- **Average tokens per query** - Average token usage per website type
- **Min/Max tokens** - Range of token usage within each category
- **Comparison** - How much more/less documentation sites use compared to normal sites

## Adding New Queries

Edit `queries.txt` to add more test queries. Keep the format:

```
# Normal Web Search Queries
your normal query here
another normal query

# Documentation/Technical Queries
your technical query here
another docs query
```

## Example Output

```
TOKEN USAGE SUMMARY
============================================================

NORMAL WEBSITES:
  Total queries: 10
  Successful: 9
  Failed: 1
  Total tokens: 45,230
  Average tokens per query: 5,026
  Min tokens: 2,100
  Max tokens: 8,900

DOCUMENTATION WEBSITES:
  Total queries: 10
  Successful: 10
  Failed: 0
  Total tokens: 67,450
  Average tokens per query: 6,745
  Min tokens: 3,200
  Max tokens: 12,100

COMPARISON:
  Documentation sites use +1,719 tokens on average
  That's +34.2% compared to normal websites
```

This helps you understand the token requirements for different types of content when using web2md.