# eCom/urls.py
from django.urls import path
from . import views

'''
This represents the url patterns for the eCom app.
'''

urlpatterns = [

    # Welcome page
    path("", views.welcome_view, name="welcome"),

    # Registration page
    path("register/", views.register_user, name="register"),

    # Login page
    path("login/", views.login_user, name="login"),

    # Logout page
    path("logout/", views.logout_user, name="logout"),

    # Request password reset page with user email as input
    path("request_reset/", views.send_password_reset, name="request_reset"),

    # Page when users use their reset link from the email
    path("reset/<str:token>/", views.reset_password, name="reset_password"),

    # Vendor homepage
    path("vendor-home/", views.vendor_home, name="vendor_home"),

    # Stores detail page
    path("store/<int:pk>/", views.stores_detail, name="stores_detail"),

    # Stores create page
    path("store/new/", views.stores_create, name="stores_create"),

    # Stores update page
    path("stores/<int:pk>/edit", views.stores_update, name="stores_update"),

    # Stores delete page
    path("stores/<int:pk>/delete", views.stores_delete, name="stores_delete"),

    # Buyer homepage
    path("buyer-home/", views.buyer_home, name="buyer_home"),

    # Products detail vendor page
    path(
        "product/<int:pk>/vendor",
        views.products_detail_vendor,
        name="products_detail_vendor"
    ),

    # Products create page
    path(
        "stores/<int:store_pk>/product/new/",
        views.products_create,
        name="products_create"
    ),

    # Products update page
    path(
        "product/<int:pk>/edit/",
        views.products_update,
        name="products_update"
    ),

    # Products delete page
    path(
        "product/<int:pk>/delete/",
        views.products_delete,
        name="products_delete"
    ),

    # Products detail buyer page
    path(
        "product/<int:pk>/",
        views.products_detail_buyer,
        name="products_detail_buyer"
    ),

    # Url to add item to cart in session
    path(
        "cart/add/<int:prod_pk>/",
        views.add_to_cart,
        name="add_to_cart"
    ),

    # User cart page
    path("cart/", views.user_cart, name="user_cart"),

    # Clear user cart
    path("cart/clear/", views.clear_cart, name="clear_cart"),

    # Checkout and order confirmation page
    path("order/confirm/", views.check_out, name="check_out"),

    # Review page
    path(
        "product/<int:pk>/review/",
        views.add_review,
        name="add_review"
    ),

    # Url's for API endpoitns
    # Register API
    path(
        "api/register/",
        views.register_user_api,
        name="register_api"
    ),

    # Create Stores API
    path(
        "api/stores/create/",
        views.stores_create_api,
        name="create_stores_api"
    ),

    # Add Products API
    path(
        "api/<int:store_id>/product/add/",
        views.add_product_api,
        name="product_add_api"
    ),

    # Retrieve Reviews API
    path(
        "api/reviews/",
        views.retrieve_reviews_api,
        name="reviews_api"
    ),

    # Retrieve stores API
    path(
        "api/stores_products/view/",
        views.retrieve_stores_products_api,
        name="stores_products_view_api"
    ),
]
