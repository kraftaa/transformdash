"""
External Data Sources API Integration
Fetches public data from various APIs for map visualization
"""
import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from functools import lru_cache
import os

logger = logging.getLogger(__name__)


class ElectricityPricesFetcher:
    """Fetch electricity prices per county from EIA API"""

    def __init__(self):
        self.eia_api_key = os.getenv('EIA_API_KEY', '')  # Get from .env
        self.base_url = "https://api.eia.gov/v2"

    @lru_cache(maxsize=1)
    def get_electricity_prices_by_state(self) -> pd.DataFrame:
        """
        Get electricity prices by state from EIA
        Returns DataFrame with columns: state, price_cents_per_kwh, year
        """
        try:
            # EIA API endpoint for electricity prices
            url = f"{self.base_url}/electricity/retail-sales/data/"
            params = {
                'frequency': 'annual',
                'data[0]': 'price',
                'facets[sectorid][]': 'RES',  # Residential sector
                'sort[0][column]': 'period',
                'sort[0][direction]': 'desc',
                'offset': 0,
                'length': 5000
            }

            if self.eia_api_key:
                params['api_key'] = self.eia_api_key

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'response' in data and 'data' in data['response']:
                df = pd.DataFrame(data['response']['data'])
                df = df.rename(columns={
                    'stateid': 'state_code',
                    'price': 'price_cents_per_kwh',
                    'period': 'year'
                })
                return df[['state_code', 'price_cents_per_kwh', 'year']]

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching electricity prices: {e}")
            return pd.DataFrame()


class AirQualityFetcher:
    """Fetch air quality data per county from EPA AQS API"""

    def __init__(self):
        self.epa_email = os.getenv('EPA_EMAIL', 'test@test.com')
        self.epa_key = os.getenv('EPA_KEY', 'test')
        self.base_url = "https://aqs.epa.gov/data/api"

    @lru_cache(maxsize=1)
    def get_air_quality_by_county(self, state_code: str = '06', year: int = 2023) -> pd.DataFrame:
        """
        Get AQI data by county from EPA
        state_code: 2-digit FIPS state code (e.g., '06' for California)
        Returns DataFrame with columns: state, county, aqi, date
        """
        try:
            # EPA AQS API endpoint for daily summary data
            url = f"{self.base_url}/annualData/byState"
            params = {
                'email': self.epa_email,
                'key': self.epa_key,
                'param': '88101',  # PM2.5 parameter code
                'bdate': f"{year}0101",
                'edate': f"{year}1231",
                'state': state_code
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'Data' in data:
                df = pd.DataFrame(data['Data'])
                df = df.rename(columns={
                    'state_code': 'state',
                    'county_code': 'county',
                    'arithmetic_mean': 'avg_pm25'
                })
                return df[['state', 'county', 'avg_pm25']]

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching air quality data: {e}")
            return pd.DataFrame()


class DataCentersFetcher:
    """Fetch data centers locations"""

    @lru_cache(maxsize=1)
    def get_data_centers(self) -> pd.DataFrame:
        """
        Fetch data centers from Aterio.io or similar source
        Returns DataFrame with columns: name, city, state, lat, lon, capacity_mw

        Note: For now returns sample data. In production, you would:
        1. Download the CSV/JSON from https://www.aterio.io/datasets/lst_us_data_centers
        2. Parse and return the data
        """
        try:
            # Sample data structure
            # In production, fetch from actual API or CSV file
            sample_data = {
                'name': [
                    'Ashburn Data Center',
                    'Silicon Valley Hub',
                    'Dallas Tech Center'
                ],
                'city': ['Ashburn', 'San Jose', 'Dallas'],
                'state': ['VA', 'CA', 'TX'],
                'county': ['Loudoun', 'Santa Clara', 'Dallas'],
                'lat': [39.0438, 37.3382, 32.7767],
                'lon': [-77.4874, -121.8863, -96.7970],
                'capacity_mw': [500, 300, 200]
            }

            return pd.DataFrame(sample_data)

        except Exception as e:
            logger.error(f"Error fetching data centers: {e}")
            return pd.DataFrame()


class IndustryFactoriesFetcher:
    """Fetch industry factories locations from Census data"""

    @lru_cache(maxsize=1)
    def get_manufacturing_by_county(self) -> pd.DataFrame:
        """
        Get manufacturing establishments by county from Census Bureau
        Uses County Business Patterns (CBP) data

        Returns DataFrame with columns: state, county, naics_code,
                                       establishments_count, employees

        Note: Census API requires an API key from https://api.census.gov/data/key_signup.html
        """
        try:
            census_api_key = os.getenv('CENSUS_API_KEY', '')

            if not census_api_key:
                # Return sample data if no API key
                return self._get_sample_manufacturing_data()

            # Census County Business Patterns API
            base_url = "https://api.census.gov/data/2021/cbp"
            params = {
                'get': 'NAME,ESTAB,EMP',
                'for': 'county:*',
                'NAICS2017': '31-33',  # Manufacturing sector
                'key': census_api_key
            }

            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # First row is headers
            headers = data[0]
            rows = data[1:]

            df = pd.DataFrame(rows, columns=headers)
            df = df.rename(columns={
                'NAME': 'county_name',
                'ESTAB': 'establishments',
                'EMP': 'employees',
                'state': 'state_code',
                'county': 'county_code'
            })

            return df

        except Exception as e:
            logger.error(f"Error fetching manufacturing data: {e}")
            return self._get_sample_manufacturing_data()

    def _get_sample_manufacturing_data(self) -> pd.DataFrame:
        """Return sample manufacturing data"""
        sample_data = {
            'county_name': ['Los Angeles County', 'Cook County', 'Harris County'],
            'state_code': ['06', '17', '48'],
            'county_code': ['037', '031', '201'],
            'state_name': ['California', 'Illinois', 'Texas'],
            'establishments': [8500, 5200, 4800],
            'employees': [125000, 85000, 78000]
        }
        return pd.DataFrame(sample_data)


class USCountiesFetcher:
    """Fetch US counties GeoJSON for map visualization"""

    @lru_cache(maxsize=1)
    def get_counties_geojson(self) -> dict:
        """
        Get US counties boundaries as GeoJSON
        Uses publicly available county boundaries from US Census
        """
        try:
            # US Census Bureau county boundaries (5m resolution)
            url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Error fetching counties GeoJSON: {e}")
            return {"type": "FeatureCollection", "features": []}


# Create singleton instances
electricity_fetcher = ElectricityPricesFetcher()
air_quality_fetcher = AirQualityFetcher()
data_centers_fetcher = DataCentersFetcher()
factories_fetcher = IndustryFactoriesFetcher()
counties_fetcher = USCountiesFetcher()


# Helper function to combine all data sources
def get_county_map_data() -> Dict:
    """
    Combine all data sources into a single response for map visualization
    """
    try:
        return {
            'counties_geojson': counties_fetcher.get_counties_geojson(),
            'electricity_prices': electricity_fetcher.get_electricity_prices_by_state().to_dict('records'),
            'air_quality': air_quality_fetcher.get_air_quality_by_county().to_dict('records'),
            'data_centers': data_centers_fetcher.get_data_centers().to_dict('records'),
            'manufacturing': factories_fetcher.get_manufacturing_by_county().to_dict('records')
        }
    except Exception as e:
        logger.error(f"Error combining map data: {e}")
        return {}
