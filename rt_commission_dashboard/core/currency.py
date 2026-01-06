from rt_commission_dashboard.core.config import config

def format_currency(value):
    """
    Formats a numeric value based on the configured currency.
    - USD: $1,234.56
    - VND: 1,234,567 ₫
    """
    currency = config.get_currency()
    if value is None:
        value = 0.0
        
    if currency == 'vnd':
        # VND usually has no decimals, uses dots or commas. 
        # Standard: 1,234,567 ₫
        return f"{value:,.0f} ₫"
    else:
        # USD default
        return f"${value:,.2f}"
