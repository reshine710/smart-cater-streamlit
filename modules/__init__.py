# Modules for Smart Vending Machine Backend UI

from .dashboard import dashboard_page
from .machine_status import machine_status_page
from .menu_management import menu_management_page
from .recipe_settings import recipe_settings_page
from .sales_analytics import sales_analytics_page
from .ai_recommendations import ai_recommendations_page
from .location_management import location_management_page
from .order_management import order_management_page
from .inventory_management import inventory_management_page

__all__ = [
    'dashboard_page',
    'machine_status_page', 
    'menu_management_page',
    'recipe_settings_page',
    'sales_analytics_page',
    'ai_recommendations_page',
    'location_management_page',
    'order_management_page',
    'inventory_management_page'
]
