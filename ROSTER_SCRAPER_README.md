# Arlington Recreation Roster Scraper

This script logs into the Arlington Recreation portal and scrapes roster information for all Arlington Youth Futsal League programs.

## Features

- Automatically logs into arlingtonma.myrec.com
- Finds all "Arlington Youth Futsal League" programs
- Extracts:
  - Program names (e.g., "Boys Grades 7 & 8", "Girls Grades 1 & 2")
  - Dates, times, and locations
  - Coach/instructor names
  - Enrollment statistics (Max, Enrolled, Waitlist, Resident/Non-Resident breakdowns)
  - All participant names
- Exports everything to a formatted Excel file

## Prerequisites

Install required dependencies:

```bash
pip install selenium webdriver-manager openpyxl beautifulsoup4
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Setup

### Option 1: Environment Variables (Recommended)

Add your credentials to `.env` file:

```bash
ARLINGTON_USERNAME=your_email@example.com
ARLINGTON_PASSWORD=your_password
```

Then run:

```bash
python roster_scraper.py
```

### Option 2: Interactive Prompt

Simply run the script and enter credentials when prompted:

```bash
python roster_scraper.py
```

## Usage

```bash
python roster_scraper.py
```

The script will:

1. Launch Chrome browser (you'll see it open)
2. Navigate to the Arlington Recreation login page
3. Log in with your credentials
4. Navigate to the coaches/rosters page
5. Find all futsal league programs
6. Extract roster data for each program
7. Export to Excel file: `futsal_rosters_YYYY-MM-DD_HHMMSS.xlsx`

## Output

The Excel file will contain columns:

| Column | Description |
|--------|-------------|
| Program Name | Full program name (e.g., "Arlington Youth Futsal League - Boys Grades 7 & 8") |
| Dates | Session dates (e.g., "Saturday, January 10, 2026 - Saturday, March 7, 2026") |
| Times | Session times |
| Location | Facility location |
| Max | Maximum enrollment |
| Enrolled | Total enrolled |
| Waitlist | Number on waitlist |
| Res Max | Resident maximum |
| Res Enrolled | Residents enrolled |
| Non-Res Max | Non-resident maximum |
| Non-Res Enrolled | Non-residents enrolled |
| Coaches | List of coaches/instructors |
| Participants | List of all participant names |

## Troubleshooting

### Login Issues

If login fails:
- Check your credentials in `.env` file
- Make sure you can log in manually at https://arlingtonma.myrec.com
- Check if the site requires 2FA (the script doesn't support this yet)

### No Programs Found

If no futsal programs are found:
- The script saves `page_source.html` for inspection
- The page structure may have changed
- You may need to navigate to a different page after login
- Contact the developer with the `page_source.html` file

### Chrome Driver Issues

If you get Chrome driver errors:
- Make sure Chrome browser is installed
- The script will automatically download the correct ChromeDriver version
- Try updating Chrome to the latest version

### Page Structure Changed

The Arlington Recreation website may change its HTML structure. If the scraper stops working:
1. Check `page_source.html` generated during scraping
2. You may need to update the CSS selectors in the script
3. Look for elements with IDs, classes, or text containing:
   - "Arlington Youth Futsal League"
   - "Roster"
   - "Max", "Enrolled", "Waitlist"

## Advanced Usage

### Run in Headless Mode

Edit `roster_scraper.py` and change:

```python
scraper = ArlingtonRosterScraper(username, password, headless=True)
```

This will run without opening a visible browser window.

### Custom Export Filename

Modify the `export_to_excel()` call:

```python
scraper.export_to_excel(filename="my_custom_rosters.xlsx")
```

## Notes

- The browser window will stay open for 2 seconds after completion so you can see what happened
- The script is configured to run in non-headless mode by default for easier debugging
- Participant names and coach names are stored as multi-line text in Excel cells
- The Excel file has auto-adjusted column widths and header formatting

## Privacy & Security

- Never commit your `.env` file with real credentials
- The `.gitignore` file should exclude `.env`
- Your credentials are only used to log into the portal and are not stored or transmitted anywhere else
- The script runs entirely on your local machine

## Support

If you encounter issues:
1. Check that you can log in manually to the website
2. Review `page_source.html` to see the actual page content
3. Check for any error messages in the console output
4. Ensure all dependencies are installed correctly
