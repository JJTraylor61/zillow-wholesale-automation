"""
Zillow Wholesale Property Automation
Main scraping and analysis engine
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import json
from datetime import datetime

class ZillowWholesaleScraper:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.properties = []
        
    def setup_driver(self):
        """Initialize Chrome driver with stealth settings"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    def build_search_url(self):
        """Build Zillow search URL from user config"""
        base_url = "https://www.zillow.com/homes/for_sale/"
        
        # Location
        if self.config['location_type'] == 'county':
            location = f"{self.config['county']}-{self.config['state']}"
        else:
            location = self.config['zip_code']
        
        # Build filter parameters
        filters = {
            'searchQueryState': {
                'pagination': {},
                'usersSearchTerm': location,
                'mapBounds': {},
                'isMapVisible': True,
                'filterState': {
                    'sortSelection': {'value': 'days'},  # Sort by days on market
                    'daysOnZillow': {'min': 30},  # 30+ days minimum
                    'price': {
                        'min': self.config.get('min_price', 50000),
                        'max': self.config.get('max_price', 300000)
                    }
                }
            }
        }
        
        # Add property type filters
        if self.config['property_types']['single_family']:
            filters['searchQueryState']['filterState']['homeType'] = {'in': [6]}  # Single family
        
        return f"{base_url}{location}/"
    
    def search_properties(self):
        """Execute the property search"""
        if not self.driver:
            self.setup_driver()
        
        search_url = self.build_search_url()
        print(f"Searching: {search_url}")
        
        self.driver.get(search_url)
        time.sleep(3)  # Let page load
        
        # Wait for property cards to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='property-card']"))
            )
        except:
            print("No properties found or page didn't load properly")
            return []
        
        # Extract property data
        property_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-test='property-card']")
        
        for card in property_cards[:self.config.get('max_results', 10)]:  # Limit results
            property_data = self.extract_property_data(card)
            if property_data:
                self.properties.append(property_data)
        
        return self.properties
    
    def extract_property_data(self, card):
        """Extract data from individual property card"""
        try:
            # Basic property info
            address = card.find_element(By.CSS_SELECTOR, "[data-test='property-card-addr']").text
            price = card.find_element(By.CSS_SELECTOR, "[data-test='property-card-price']").text
            
            # Property details
            details = card.find_elements(By.CSS_SELECTOR, "[data-test='property-card-details'] span")
            beds, baths, sqft = "N/A", "N/A", "N/A"
            
            if len(details) >= 3:
                beds = details[0].text.replace(' bd', '')
                baths = details[1].text.replace(' ba', '')
                sqft = details[2].text.replace(' sqft', '').replace(',', '')
            
            # Days on market (if available)
            dom_element = card.find_elements(By.XPATH, ".//*[contains(text(), 'days on Zillow')]")
            days_on_market = dom_element[0].text.split()[0] if dom_element else "Unknown"
            
            # Property link for more details
            link_element = card.find_element(By.CSS_SELECTOR, "a")
            property_url = link_element.get_attribute('href')
            
            return {
                'address': address,
                'price': price,
                'bedrooms': beds,
                'bathrooms': baths,
                'square_feet': sqft,
                'days_on_market': days_on_market,
                'url': property_url,
                'scraped_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error extracting property data: {e}")
            return None
    
    def analyze_deals(self):
        """Analyze each property for wholesale opportunity"""
        analyzed_properties = []
        
        for prop in self.properties:
            analysis = self.calculate_opportunity_score(prop)
            prop.update(analysis)
            analyzed_properties.append(prop)
        
        return analyzed_properties
    
    def calculate_opportunity_score(self, property_data):
        """Calculate deal score and recommended action"""
        score = 0
        
        # Days on market scoring
        try:
            dom = int(property_data['days_on_market'])
            if dom > 120: score += 40
            elif dom > 90: score += 30
            elif dom > 60: score += 20
        except:
            score += 10  # Unknown DOM gets some points
        
        # Add other scoring logic here based on your criteria
        
        # Determine action
        if score >= 70:
            action = "CALL TODAY - Strong opportunity"
        elif score >= 50:
            action = "CALL THIS WEEK - Good potential"
        else:
            action = "RESEARCH MORE - Gather intel"
        
        return {
            'opportunity_score': score,
            'recommended_action': action,
            'analysis_notes': f"DOM: {property_data['days_on_market']} days"
        }
    
    def export_call_sheets(self, filename='call_sheets.csv'):
        """Export properties to CSV for call sheets"""
        if not self.properties:
            print("No properties to export")
            return
        
        df = pd.DataFrame(self.properties)
        df.to_csv(filename, index=False)
        print(f"Call sheets exported to {filename}")
        
        return filename
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()

# Example usage
if __name__ == "__main__":
    # Sample configuration
    config = {
        'location_type': 'county',
        'county': 'Wake',
        'state': 'NC',
        'property_types': {'single_family': True},
        'max_results': 10,
        'min_price': 100000,
        'max_price': 250000
    }
    
    scraper = ZillowWholesaleScraper(config)
    
    try:
        properties = scraper.search_properties()
        analyzed = scraper.analyze_deals()
        scraper.export_call_sheets()
        
        print(f"Found {len(properties)} properties")
        for prop in analyzed:
            print(f"{prop['address']}: {prop['recommended_action']}")
            
    finally:
        scraper.cleanup()
