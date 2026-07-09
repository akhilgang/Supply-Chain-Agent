# app/tools/fx.py
from semantic_kernel.functions import kernel_function
import requests

class FxTools:
    @kernel_function(name="convert_fx", description="Convert currency via Frankfurter")
    def convert_fx(self, amount: float, base: str, target: str):
        """
        Convert currency using the Frankfurter API.

        Args:
            amount: Amount to convert
            base: Source currency code (e.g., USD)
            target: Target currency code (e.g., EUR)

        Returns:
            JSON response with conversion rates

        TODO: Implement currency conversion API call
        - Frankfurter API endpoint: https://api.frankfurter.app/latest
        - Query params: amount, from (base currency), to (target currency)
        - Use requests.get() with timeout and return .json() response
        """
        try:
            resp = requests.get(
                "https://api.frankfurter.app/latest",
                params={"amount": amount, "from": base, "to": target},
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": f"Currency conversion failed: {e}"}
