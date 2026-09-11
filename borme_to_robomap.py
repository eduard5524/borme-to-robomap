#!/usr/bin/env python3
"""
BORME to Robomap Integration
============================
Fetches Spanish business data from official BORME records (BOE)
and submits it to Robomap Cloud API.

Requirements:
    pip install -r requirements.txt

Setup:
    1. Create a .env file with your Robomap credentials:
        ROBOMAP_EMAIL=your@email.com
        ROBOMAP_PASSWORD=your_password
    
    2. Run the script:
        python borme_to_robomap.py
"""

import json
import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BORME_API_BASE = "https://www.boe.es/datosabiertos/api/borme/sumario"
ROBOMAP_API_BASE = "https://api.robomap.ai"
ROBOMAP_WEB_BASE = "https://app.robomap.ai/api"


class BORMEFetcher:
    """Fetch business data from official Spanish BORME records."""
    
    def __init__(self, api_base: str = BORME_API_BASE):
        self.api_base = api_base
    
    def get_daily_summary(self, date: str) -> Dict[str, Any]:
        """
        Fetch BORME summary for a specific date.
        
        Args:
            date: Date in YYYYMMDD format (e.g., "20260912")
        
        Returns:
            JSON response with BORME summary data
        """
        url = f"{self.api_base}/{date}"
        print(f"Fetching BORME data for {date}...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching BORME data: {e}")
            raise
    
    def get_recent_summaries(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch BORME summaries for the last N days.
        
        Args:
            days: Number of days to fetch (default: 7)
        
        Returns:
            List of BORME summary dictionaries
        """
        summaries = []
        today = datetime.now()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            
            try:
                summary = self.get_daily_summary(date_str)
                summaries.append(summary)
                print(f"✓ Fetched data for {date_str}")
            except Exception as e:
                print(f"✗ Failed to fetch {date_str}: {e}")
        
        return summaries
    
    def extract_companies(self, summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract company information from BORME summaries.
        
        Args:
            summaries: List of BORME summary dictionaries
        
        Returns:
            List of company dictionaries with standardized fields
        """
        companies = []
        
        for summary in summaries:
            if not isinstance(summary, dict):
                continue
            
            # Navigate BORME structure
            data = summary.get('data', {})
            sumario = data.get('sumario', {})
            diario = sumario.get('diario', [])
            
            for issue in diario:
                if not isinstance(issue, dict):
                    continue
                
                issue_number = issue.get('numero', 'Unknown')
                sumario_diario = issue.get('sumario_diario', {})
                
                # Extract companies from different sections
                for section_key in ['empresas', 'sociedades', 'entidades']:
                    section = sumario_diario.get(section_key, [])
                    
                    if isinstance(section, list):
                        for company in section:
                            if isinstance(company, dict):
                                extracted = self._normalize_company(company, issue_number)
                                if extracted:
                                    companies.append(extracted)
        
        print(f"\nExtracted {len(companies)} companies from BORME data")
        return companies
    
    def _normalize_company(self, company: Dict[str, Any], issue_number: str) -> Optional[Dict[str, Any]]:
        """Normalize company data to standard format."""
        try:
            return {
                'name': company.get('nombre', company.get('name', 'Unknown')),
                'cif': company.get('cif', company.get('nif', '')),
                'legal_form': company.get('forma_juridica', company.get('legal_form', '')),
                'address': company.get('domicilio', company.get('address', '')),
                'city': company.get('municipio', company.get('city', '')),
                'province': company.get('provincia', company.get('province', '')),
                'postal_code': company.get('cp', company.get('postal_code', '')),
                'cnae': company.get('cnae', ''),
                'activity': company.get('actividad', company.get('activity', '')),
                'status': company.get('estado', company.get('status', 'active')),
                'registration_date': company.get('fecha_inscripcion', ''),
                'borme_issue': issue_number,
                'source': 'BORME',
                'country': 'ES'
            }
        except Exception as e:
            print(f"Error normalizing company: {e}")
            return None


class RobomapClient:
    """Client for Robomap Cloud API."""
    
    def __init__(self, email: str, password: str, api_base: str = ROBOMAP_API_BASE):
        self.api_base = api_base
        self.email = email
        self.password = password
        self.access_token = None
        self.user_id = None
    
    def login(self) -> bool:
        """
        Authenticate with Robomap and obtain access token.
        
        Returns:
            True if login successful, False otherwise
        """
        url = f"{self.api_base}/auth/login"
        
        print(f"Authenticating with Robomap as {self.email}...")
        
        try:
            response = requests.post(url, json={
                'email': self.email,
                'password': self.password
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.user_id = data.get('user', {}).get('id')
                
                print(f"✓ Successfully authenticated!")
                print(f"  User ID: {self.user_id}")
                return True
            else:
                print(f"✗ Authentication failed: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def create_business_profile(self, company: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a business profile in Robomap from company data.
        
        Args:
            company: Normalized company dictionary
        
        Returns:
            Response data if successful, None otherwise
        """
        if not self.access_token:
            print("✗ Not authenticated. Call login() first.")
            return None
        
        url = f"{self.api_base}/account/business-profile"
        
        # Map BORME data to Robomap business profile format
        payload = {
            'name': company.get('name', 'Unknown Business'),
            'legal_name': company.get('name'),
            'tax_id': company.get('cif', ''),
            'legal_form': company.get('legal_form', ''),
            'address': {
                'street': company.get('address', ''),
                'city': company.get('city', ''),
                'province': company.get('province', ''),
                'postal_code': company.get('postal_code', ''),
                'country': company.get('country', 'ES')
            },
            'industry': company.get('cnae', ''),
            'activity_description': company.get('activity', ''),
            'status': 'active' if company.get('status') == 'active' else 'inactive',
            'metadata': {
                'source': 'BORME',
                'borme_issue': company.get('borme_issue', ''),
                'registration_date': company.get('registration_date', '')
            }
        }
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                print(f"✓ Created business profile: {company.get('name')}")
                return response.json()
            else:
                print(f"✗ Failed to create profile for {company.get('name')}: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error creating profile: {e}")
            return None
    
    def create_data_record(self, company: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a workspace data record in Robomap.
        
        Alternative method using /data endpoint.
        
        Args:
            company: Normalized company dictionary
        
        Returns:
            Response data if successful, None otherwise
        """
        if not self.access_token:
            print("✗ Not authenticated. Call login() first.")
            return None
        
        url = f"{self.api_base}/data"
        
        payload = {
            'type': 'business',
            'data': {
                'name': company.get('name'),
                'cif': company.get('cif'),
                'address': company.get('address'),
                'city': company.get('city'),
                'province': company.get('province'),
                'cnae': company.get('cnae'),
                'activity': company.get('activity'),
                'status': company.get('status'),
                'source': 'BORME',
                'borme_issue': company.get('borme_issue')
            }
        }
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                print(f"✓ Created data record: {company.get('name')}")
                return response.json()
            else:
                print(f"✗ Failed to create data record: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error creating data record: {e}")
            return None
    
    def bulk_import_companies(self, companies: List[Dict[str, Any]], 
                              use_data_endpoint: bool = False) -> Dict[str, Any]:
        """
        Import multiple companies to Robomap.
        
        Args:
            companies: List of normalized company dictionaries
            use_data_endpoint: If True, use /data endpoint instead of business-profile
        
        Returns:
            Summary of import results
        """
        results = {
            'total': len(companies),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        print(f"\n{'='*60}")
        print(f"Importing {len(companies)} companies to Robomap...")
        print(f"{'='*60}\n")
        
        for i, company in enumerate(companies, 1):
            print(f"[{i}/{len(companies)}] Processing: {company.get('name', 'Unknown')}")
            
            if use_data_endpoint:
                result = self.create_data_record(company)
            else:
                result = self.create_business_profile(company)
            
            if result:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'company': company.get('name'),
                    'cif': company.get('cif')
                })
            
            # Rate limiting - be respectful to the API
            if i % 10 == 0:
                print(f"  ... pausing for rate limiting ...")
                import time
                time.sleep(1)
        
        return results


def main():
    """Main execution function."""
    print("="*60)
    print("BORME to Robomap Integration")
    print("="*60)
    print()
    
    # Get credentials from environment
    email = os.getenv('ROBOMAP_EMAIL')
    password = os.getenv('ROBOMAP_PASSWORD')
    
    if not email or not password:
        print("✗ Error: Missing Robomap credentials")
        print("\nPlease create a .env file with:")
        print("  ROBOMAP_EMAIL=your@email.com")
        print("  ROBOMAP_PASSWORD=your_password")
        return
    
    # Initialize BORME fetcher
    borme_fetcher = BORMEFetcher()
    
    # Fetch recent BORME data (last 7 days)
    print("Step 1: Fetching BORME data from BOE...")
    print("-" * 60)
    summaries = borme_fetcher.get_recent_summaries(days=7)
    
    if not summaries:
        print("✗ No BORME data retrieved. Exiting.")
        return
    
    # Extract companies
    print("\nStep 2: Extracting companies from BORME data...")
    print("-" * 60)
    companies = borme_fetcher.extract_companies(summaries)
    
    if not companies:
        print("✗ No companies extracted. Exiting.")
        return
    
    # Save extracted companies to file
    with open('borme_companies.json', 'w', encoding='utf-8') as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Saved {len(companies)} companies to borme_companies.json")
    
    # Initialize Robomap client
    print("\nStep 3: Connecting to Robomap...")
    print("-" * 60)
    robomap = RobomapClient(email, password)
    
    if not robomap.login():
        print("✗ Failed to authenticate with Robomap. Exiting.")
        return
    
    # Import companies to Robomap
    print("\nStep 4: Importing companies to Robomap...")
    print("-" * 60)
    
    # Choose import method based on your Robomap account type
    # use_data_endpoint=True for workspace data records
    # use_data_endpoint=False for business profiles (default)
    results = robomap.bulk_import_companies(companies, use_data_endpoint=False)
    
    # Print summary
    print("\n" + "="*60)
    print("Import Summary")
    print("="*60)
    print(f"Total companies:     {results['total']}")
    print(f"Successful:          {results['successful']}")
    print(f"Failed:              {results['failed']}")
    print(f"Success rate:        {results['successful']/results['total']*100:.1f}%")
    
    if results['errors']:
        print(f"\nFailed companies:")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"  - {error['company']} (CIF: {error['cif']})")
    
    print("\n✓ Import complete!")
    print(f"\nView your businesses at: https://app.robomap.ai")


if __name__ == '__main__':
    main()
