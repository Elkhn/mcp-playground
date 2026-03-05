import requests
from datetime import datetime, timedelta
from fastmcp import FastMCP
import xml.etree.ElementTree as ET

mcp = FastMCP("Currency Exchange")

CBAR_URL = "https://www.cbar.az/currencies"

CURRENCIES = ["USD", "EUR", "RUB", "AZN"]

def fetch_currency_rates(date: str = None) -> dict:
    if date:
        try:
            # Validate and convert YYYY-MM-DD -> DD.MM.YYYY
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            cbar_date = parsed_date.strftime("%d.%m.%Y")
            url = f"{CBAR_URL}/{cbar_date}.xml"
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}
    else:
        today = datetime.today().strftime("%d.%m.%Y")
        url = f"{CBAR_URL}/{today}.xml"

    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        rates = {"AZN": 1.0}  # Base currency
        for val_type in root.findall(".//Valute"):
            code = val_type.get("Code")
            if code in CURRENCIES:
                nominal = int(val_type.find("Nominal").text)
                value = float(val_type.find("Value").text.replace(",", "."))
                rates[code] = value / nominal

        return rates

    except Exception as e:
        return {"error": f"Failed to fetch currency data: {e}"}


@mcp.tool()
async def get_currency_rates(date: str = None) -> dict:
    """
    Get current or historical currency rates for USD, EUR, RUB, AZN.

    Args:
        date: Date in YYYY-MM-DD format. Optional. Defaults to today.

    Returns:
        Dictionary of currency rates.
    """
    return fetch_currency_rates(date)

@mcp.tool()
async def convert_currency(amount: float, from_currency: str, to_currency: str, date: str = None) -> dict:
    """
    Convert an amount from one currency to another using CBAR official rates.

    Args:
        amount: Amount to convert.
        from_currency: Currency code to convert from (USD, EUR, RUB, AZN).
        to_currency: Currency code to convert to (USD, EUR, RUB, AZN).
        date: Optional date in YYYY-MM-DD format. Defaults to today.

    Returns:
        Dictionary with converted amount and rate info.
    """
    rates = fetch_currency_rates(date)
    if "error" in rates:
        return rates

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency not in rates or to_currency not in rates:
        return {"error": "Unsupported currency. Choose from USD, EUR, RUB, AZN."}

    # Apply CBAR conversion logic
    if from_currency == "AZN":
        # Converting from AZN to foreign currency
        rate = 1 / rates[to_currency]
    elif to_currency == "AZN":
        # Converting from foreign currency to AZN
        rate = rates[from_currency]
    else:
        # Foreign currency to foreign currency
        rate = rates[from_currency] / rates[to_currency]

    converted = amount * rate

    return {
        "amount": amount,
        "from": from_currency,
        "to": to_currency,
        "rate": round(rate, 6),
        "converted_amount": round(converted, 4),
        "date": date or datetime.today().strftime("%Y-%m-%d")
    }


if __name__ == "__main__":
    print("Starting Currency Exchange MCP server on port 8001...")
    print("Connect to this server using http://localhost:8001/sse")
    mcp.run(transport="sse", host="0.0.0.0", port=8001)