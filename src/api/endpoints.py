from .http_interceptor import HTTPInterceptor


class APIEndpoints:
    def __init__(self):
        """Initialize the API client."""
        self.interceptor = HTTPInterceptor()

    def get_mercadolibre_item(self, inventory_id, query_params):
        """Example of using the interceptor for the `get_items` API endpoint.

        Args:
            inventory_id (str): The ID of the item to retrieve.
            query_params (dict): The query parameters for the request.

        Returns:
            dict or None: The response data if successful, None otherwise.
        """
        endpoint = f"/mercadolibre/items/{inventory_id}"
        print(f"ENDPOINT ===========> {endpoint}")
        response = self.interceptor.request("GET", endpoint, params=query_params)
        if response and response.status_code == 200:
            return response.json()
        return None

    # def create_item(self, data):
    #     """Example of a POST request to create a new item.
    #
    #     Args:
    #         data (dict): The payload to create a new item.
    #
    #     Returns:
    #         dict or None: The response data if successful, None otherwise.
    #     """
    #     endpoint = "/items"
    #     response = self.interceptor.request("POST", endpoint, json=data)
    #     if response and response.status_code == 201:
    #         return response.json()
    #     return None
    #
    # def update_item(self, item_id, data):
    #     """Example of a PUT request to update an existing item.
    #
    #     Args:
    #         item_id (str): The ID of the item to update.
    #         data (dict): The payload containing updated fields.
    #
    #     Returns:
    #         dict or None: The response data if successful, None otherwise.
    #     """
    #     endpoint = f"/items/{item_id}"
    #     response = self.interceptor.request("PUT", endpoint, json=data)
    #     if response and response.status_code == 200:
    #         return response.json()
    #     return None
