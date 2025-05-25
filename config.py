"""
Configuration settings for Zillow Wholesale Automation
Maps UI selections to scraper parameters
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class PropertyConfig:
    """Property search configuration"""
    single_family: bool = True
    small_multifamily: bool = False
    any_age: bool = True
    built_after_1980: bool = False
    built_after_1990: bool = False
    built_after_2000: bool = False

@dataclass
class RentalStrategyConfig:
    """Rental strategy configuration"""
    market_rate: bool = True
    section_8: bool = False

@dataclass
class ManagementConfig:
    """Property management configuration"""
    property_managed: bool = True
    self_managed: bool = False
    use_default_fee: bool = True
    custom_fee: Optional[float] = None
    
    @property
    def management_fee_rate(self) -> float:
        """Calculate actual management fee rate"""
        if self.self_managed:
            return 0.0
        elif self.use_default_fee:
            return 0.10  # 10%
        else:
            return (self.custom_fee or 10.0) / 100.0

@dataclass
class LocationConfig:
    """Geographic search configuration"""
    input_method: str = "manual"  # "manual" or "import_data"
    use_county: bool = True
    use_zip: bool = False
    state: str = "NC"
    county: str = "Wake"
    zip_code: str = ""
    custom_radius: Optional[int] = None
    
    @property
    def search_radius(self) -> int:
        """Calculate search radius in miles"""
        if self.custom_radius:
            return self.custom_radius
        elif self.use_county:
            return 15  # County default
        else:
            return 5   # ZIP default

@dataclass
class InvestmentConfig:
    """Investment strategy configuration"""
    cash_purchase: bool = True
    financed_purchase: bool = False
    use_default_down: bool = True
    custom_down: Optional[float] = None
    
    @property
    def down_payment_rate(self) -> float:
        """Calculate down payment percentage"""
        if self.cash_purchase:
            return 1.0  # 100% cash
        elif self.use_default_down:
            return 0.20  # 20%
        else:
            return (self.custom_down or 20.0) / 100.0

@dataclass
class SearchConfig:
    """Main search configuration class"""
    # Core settings
    target_roi: float = 10.0
    max_results: int = 10
    min_days_on_market: int = 30
    
    # Sub-configurations
    property: PropertyConfig = PropertyConfig()
    rental_strategy: RentalStrategyConfig = RentalStrategyConfig()
    management: ManagementConfig = ManagementConfig()
    location: LocationConfig = LocationConfig()
    investment: InvestmentConfig = InvestmentConfig()
    
    # Price range (calculated dynamically)
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    
    def to_zillow_params(self) -> Dict:
        """Convert config to Zillow search parameters"""
        params = {
            'location_type': 'county' if self.location.use_county else 'zip',
            'county': self.location.county,
            'state': self.location.state,
            'zip_code': self.location.zip_code,
            'radius': self.location.search_radius,
            'max_results': self.max_results,
            'min_days_on_market': self.min_days_on_market,
            'property_types': {
                'single_family': self.property.single_family,
                'multifamily': self.property.small_multifamily
            }
        }
        
        # Add price range if calculated
        if self.min_price:
            params['min_price'] = self.min_price
        if self.max_price:
            params['max_price'] = self.max_price
            
        return params
    
    def calculate_price_range(self, avg_rent: float) -> None:
        """Calculate price range based on target ROI"""
        # Apply management fees
        net_rent = avg_rent * (1 - self.management.management_fee_rate)
        
        # Apply 50% expense rule
        monthly_noi = net_rent * 0.5
        annual_noi = monthly_noi * 12
        
        # Calculate max price based on investment type
        target_roi_decimal = self.target_roi / 100
        
        if self.investment.cash_purchase:
            max_price = annual_noi / target_roi_decimal
        else:
            # Simplified financed calculation
            down_payment_rate = self.investment.down_payment_rate
            max_price = (annual_noi / target_roi_decimal) / down_payment_rate
        
        # Set price range with buffer
        self.max_price = int(max_price * 0.85)  # 15% negotiation buffer
        self.min_price = int(max_price * 0.4)   # Don't go too low-end

# Preset configurations for different scenarios
CASH_FLOW_CONFIG = SearchConfig(
    target_roi=12.0,
    property=PropertyConfig(built_after_1980=True),
    management=ManagementConfig(property_managed=True),
    investment=InvestmentConfig(cash_purchase=True)
)

SUBJECT_TO_CONFIG = SearchConfig(
    target_roi=15.0,
    min_days_on_market=90,  # More distressed sellers
    property=PropertyConfig(any_age=True),
    management=ManagementConfig(self_managed=True),
    investment=InvestmentConfig(cash_purchase=True)
)

SECTION_8_CONFIG = SearchConfig(
    target_roi=10.0,
    rental_strategy=RentalStrategyConfig(section_8=True, market_rate=False),
    property=PropertyConfig(built_after_1980=True),
    management=ManagementConfig(property_managed=True)
)

# Environment variables for sensitive data
ZILLOW_DELAY = float(os.getenv('ZILLOW_DELAY', '2.0'))  # Seconds between requests
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

# Example usage
if __name__ == "__main__":
    # Test configuration
    config = SearchConfig()
    config.location.county = "Mecklenburg"
    config.location.state = "NC"
    config.target_roi = 15.0
    
    # Calculate price range (example with $1400 avg rent)
    config.calculate_price_range(1400.0)
    
    print("Search Configuration:")
    print(f"Location: {config.location.county}, {config.location.state}")
    print(f"Target ROI: {config.target_roi}%")
    print(f"Price Range: ${config.min_price:,} - ${config.max_price:,}")
    print(f"Management Fee: {config.management.management_fee_rate:.1%}")
    
    # Convert to Zillow parameters
    zillow_params = config.to_zillow_params()
    print("\nZillow Parameters:")
    for key, value in zillow_params.items():
        print(f"  {key}: {value}")
