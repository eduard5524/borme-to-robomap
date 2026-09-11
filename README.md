# BORME to Robomap Integration

Automatically fetch Spanish business data from official BORME records (BOE) and import them into Robomap Cloud.

## What it does

1. **Fetches data** from Spain's official commercial registry (BORME) via BOE API
2. **Extracts company information** including name, CIF/NIF, address, CNAE codes, legal form
3. **Imports to Robomap** as business profiles or workspace data records

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Create a `.env` file in the same directory:

```env
ROBOMAP_EMAIL=your@email.com
ROBOMAP_PASSWORD=your_password
```

### 3. Run the script

```bash
python borme_to_robomap.py
```

## Features

- Fetches BORME data for the last 7 days (customizable)
- Extracts structured company data from official records
- Authenticates with Robomap API automatically
- Creates business profiles or data records in Robomap
- Handles rate limiting and errors gracefully
- Saves extracted data to `borme_companies.json` for inspection

## Data Sources

- **BORME API**: https://www.boe.es/datosabiertos/api/borme/sumario/{YYYYMMDD}
- **Robomap API**: https://api.robomap.ai

## Output

The script produces:

1. **Console output** showing progress and summary
2. **borme_companies.json** - Raw extracted company data
3. **Robomap business profiles** - Imported to your account

## Customization

### Fetch different date range

Edit the `main()` function:

```python
# Change from 7 days to 30 days
summaries = borme_fetcher.get_recent_summaries(days=30)
```

### Fetch specific date

```python
# Fetch single date
summary = borme_fetcher.get_daily_summary("20260912")
companies = borme_fetcher.extract_companies([summary])
```

### Use data endpoint instead of business profiles

```python
# In main(), change:
results = robomap.bulk_import_companies(companies, use_data_endpoint=True)
```

## API Endpoints Used

### BORME (BOE)
- `GET /datosabiertos/api/borme/sumario/{YYYYMMDD}` - Daily BORME summary

### Robomap
- `POST /auth/login` - Authentication
- `POST /account/business-profile` - Create business profile
- `POST /data` - Create workspace data record (alternative)

## Troubleshooting

### Authentication fails
- Verify your Robomap email/password in `.env`
- Check if your account is active at https://app.robomap.ai

### No companies extracted
- BORME data structure may have changed
- Check `borme_companies.json` for raw data
- Adjust field mappings in `_normalize_company()`

### Rate limiting
- Script includes automatic pauses every 10 requests
- Increase pause duration if needed in `bulk_import_companies()`

## Legal Notes

- BORME data is public information from BOE (Agencia Estatal Boletines del Estado)
- Respect Robomap's Terms of Service when importing data
- This tool is for legitimate business use only

## License

MIT License - Use at your own risk.
