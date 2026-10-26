# eCom/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .utils import (
    build_email,
    gen_reset_url,
    change_user_password,
    build_invoice_email,
)
from .models import (
    ResetToken,
    Store,
    Product,
    Order,
    OrderItem,
    Review,
)
from hashlib import sha1
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal, InvalidOperation
from django.db import transaction
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
    )
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from rest_framework import status
from .serialazers import (
    RegisterUserSerializer,
    ReviewSerializer,
    ProductSerializer,
    StoreSerializer,
)

'''
This module contains all the views used by the eCom app. Views include managing
user regisration and login using authentication model to handle sessions. Other
views cover store management, product management, cart management and reviews.
'''


def register_user(request):
    '''
    View to register a user with Django authentication. Contains error handling
    for fields not completed, prevents duplication of usernames and assigns
    groups with permissions depending on user choice.

    Parameters:
    - request: HTTP request object

    Returns:
    Depending on user group selection, a rendered template for
    either buyers or vendors will be returned after registration. Initial
    template rendered is the registration form.
    '''

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        c_password = request.POST.get('conf_password')
        email = request.POST.get('email')
        role_id = request.POST.get('role_choice')

        # Check to confirm all fiels are completed
        if not username or not password or not email or not role_id or not c_password:
            messages.error(request, 'Please complete all fields.')
            return redirect('register')

        # Check if passwords match
        if password != c_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        # Check if username already exists.
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Choose another.')

            groups = Group.objects.all()
            return render(request, 'eCom/register.html', {'groups': groups})

        user = User.objects.create_user(
            username=username, password=password, email=email
        )

        try:
            role = Group.objects.get(id=role_id)
            user.groups.add(role)
        except Group.DoesNotExist:
            messages.error(request, 'Group does not exist. Contact support.')

        user.save()
        messages.success(request, 'Registration is successful.')
        login(request, user)

        if user.groups.filter(name='Vendor').exists():
            return redirect(reverse('vendor_home'))
        else:
            return redirect(reverse('buyer_home'))

    groups = Group.objects.all()
    return render(request, 'eCom/register.html', {'groups': groups})


def login_user(request):
    '''
    View to display the login form. Also has a link to either register or allow
    user to reset password if forgotten. Contians error handling for incorrect
    cridentials supplied. Also sets session expiry to prevent indefinite
    sessions.

    Parameters:
    - request: HTTP request object.

    Returns:
    Depending on the users assigned group, the relevant group template will be
    rendered. The initial template rendered is the login form.
    '''

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Set the session to expire in 5 days
            request.session.set_expiry(432000)

            if user.groups.filter(name='Vendor').exists():
                return redirect(reverse('vendor_home'))
            else:
                return redirect(reverse('buyer_home'))

        else:
            messages.error(request, 'Invalid cridentials.')
            return render(request, 'eCom/login.html')

    return render(request, 'eCom/login.html')


def logout_user(request):
    '''
    View to logout the user and automatically terminates the current session.

    Parameters:
    - request: HTTP request object.

    Returns:
    Renders the welcome page template after successful logout.
    '''

    if request.user is not None:
        logout(request)
        return redirect(reverse('welcome'))


def send_password_reset(request):
    '''
    View to request the user's email address to reset a forgotten password.
    A failsafe is built in on the return to state that the email has been sent
    even if the user does not exist in the database, although an email will
    only be sent to a registered user. The view makes use of functions from the
    utils module (gen_reset_url() and build_email()) to generate a secure token
    for password reset and to generate the email to be sent to the user.

    Parameters:
    - request: HTTP request object.

    Returns:
    Irrespective of the email being registered or not, the view renders a
    confirmation template to confirm email has been sent. The initial template
    generated is the request for email form.
    '''

    if request.method == 'POST':
        user_email = request.POST.get('email')

        # try loop to run the token generator and send email if the user exists
        # or to render the confirmation page again as safeguard.
        try:
            user = User.objects.get(email=user_email)
            reset_url = gen_reset_url(user)
            email = build_email(user, reset_url)
            email.send()

            return render(request, 'eCom/reset_email_sent.html', {
                'email': user_email
            })

        except ObjectDoesNotExist:
            return render(request, 'eCom/reset_email_sent.html', {
                'email': user_email
            })

    return render(request, 'eCom/request_password_reset.html')


def reset_password(request, token=None):
    '''
    View to allow user to reset a password. The view evaluates the generated
    token from the send_password_reset view and if successful, generates a
    reset form for the user to reset their password. The function
    change_user_password() from the utils module is used to reset the user's
    password.

    Parameters:
    - request: HTTP request object.
    - token: The generated token from the send_reset_email view.

    Returns:
    If the token has expired, is invalid or does not exist, the view renders a
    template to warn the user that the token is invalid. The view also checks
    if all inputs are provided and if the supplied passwords match. The user is
    redirected to the login template after successfull reset. The initial
    template generated if the token is accepted is the password reset form.
    '''

    # check token validity for the user from the ResetToken model.
    if not token:
        return render(request, 'eCom/password_reset_invalid.html')

    hashed_token = sha1(token.encode()).hexdigest()
    try:
        reset_token = ResetToken.objects.get(token=hashed_token)

        if reset_token.expiry_date < timezone.now():
            reset_token.delete()
            return render(request, 'eCom/password_reset_invalid.html')

    except ResetToken.DoesNotExist:
        return render(request, 'eCom/password_reset_invalid.html')

    # Obtain input from the user and change the password after succesful inputs
    if request.method == 'POST':
        username = reset_token.user.username
        password = request.POST.get('password')
        conf_password = request.POST.get('conf_password')

        if not password or not conf_password:
            messages.error(request, 'Please fill in all fields.')
            return render(
                request,
                'eCom/password_reset.html',
                {'token': token}
            )

        if password != conf_password:
            messages.error(request, 'Passwords do not match.')
            return render(
                request,
                'eCom/password_reset.html',
                {'token': token}
            )

        try:
            change_user_password(username, password)
            reset_token.delete()

            messages.success(request, 'Password reset successfully.')
            return redirect(reverse('login'))

        except (User.DoesNotExist, ResetToken.DoesNotExist):
            return render(request, 'eCom/password_reset_invalid.html')

    return render(request, 'eCom/password_reset.html', {'token': token})


@login_required(login_url='login')
def vendor_home(request):
    '''
    View for the dashboard of a registered vendor. This view requires a user to
    be logged in and also to have a view_stores permission. When logged in, the
    user will be able to view their current stores if any is created or be
    allowed to navigate to other views to create, edit and delete stores.

    Parameters:
    - request: HTTP request object.

    Returns:
    If a user has permission, the vendor dashboard template will be rendered
    for the specific user else they will be redirected to either the buyer home
    page or to the login template.
    '''

    if not request.user.has_perm("eCom.view_stores"):
        messages.error(request, "Access Denied: Please resister as a Vendor.")
        return redirect(reverse('buyer_home'))

    # Fetch stores for the current user.
    user_stores = Store.objects.filter(user=request.user)

    return render(request, 'eCom/vendor_home.html', {'stores': user_stores})


@login_required(login_url='login')
def stores_detail(request, pk):
    '''
    View to display the details of a specific store for a spesific user. This
    view requiers users to be logged in and have permission to view stores and
    to add products. If the user does not have these permission, they will be
    redirected accordingly. If products for the store exists, it will also
    display here and provides links to edit or delete the store as well as add,
    edit and delete products.

    Parameters:
    - request: HTTP request object.
    - pk: primary key of the specific store.

    Returns:
    If the permission check fails, the user will be redirected to the buyer
    home page. If the store does not belong to the current user, a 404 error
    will be displayed. If all checks pass, the store detail template will be
    rendered.
    '''

    # Check permissions of user
    if not request.user.has_perms(["eCom.view_stores", "eCom.add_products"]):
        messages.error(request, "Access Denied: You do not own this store.")
        return redirect(reverse('buyer_home'))

    # Fetch the store and prodducts linked to the store for user
    store = get_object_or_404(Store, pk=pk, user=request.user)
    products = Product.objects.filter(vendor=store)

    context = {
        'store': store,
        'products': products,
    }

    return render(request, 'eCom/stores_detail.html', context)


@login_required(login_url='login')
def stores_create(request):
    '''
    View for users to create a store. This view requires users to be logged in
    and to have permission to add a store.

    Parameters:
    - request: HTTP request object.

    Returns:
    If the user does not have permission, the view redirects to the buyer home
    page. If all fields are not provdided an error message will display. The
    user is redirected to their dashboard after successful store creation. The
    initial template rendered is the store form.
    '''

    # Check permission of the user
    if not request.user.has_perm("eCom.add_stores"):
        messages.error(request, "Access Denied: Please register as a Vendor.")
        return redirect(reverse('buyer_home'))

    if request.method == "POST":
        name = request.POST.get('store_name')
        description = request.POST.get('store_description')

        # Confirm all inputs are supplied
        if not name or not description:
            messages.error(request, "All fields are required.")
            return render(request, "eCom/stores_form.html", {'store': None})

        # Create a new store using the Store model.
        new_store = Store(
            name=name,
            description=description,
            user=request.user
        )
        new_store.save()

        messages.success(request, "New store created successfully.")
        return redirect(reverse("vendor_home"))

    return render(request, "eCom/stores_form.html", {'store': None})


@login_required(login_url='login')
def stores_update(request, pk):
    '''
    View to allow users to update stores. The view requires as user to be
    logged in and requires permission to change stores. It makes thakes the
    input and saves the updates to the Store database.

    Parameters:
    - request: HTTP request object.
    - pk: The primary key of the store being updated.

    Returns:
    If the user does not have the required permissions the view redirects to
    the byuer home page. If the user does not enter all the required fields,
    the view renders the store form again with an error. After successful
    update, the view redirects the user to the vendor dashboard. The initial
    template rendered is the store form.
    '''

    # Check the user permissions.
    if not request.user.has_perm("eCom.change_stores"):
        messages.error(request, "Access Denied: You cannot edit stores")
        return redirect(reverse("buyer_home"))

    # Fetch the specific store for the user.
    store = get_object_or_404(Store, pk=pk, user=request.user)

    if request.method == "POST":
        name = request.POST.get("store_name")
        description = request.POST.get("store_description")

        if not name or not description:
            messages.error(request, "All fields are required.")
            return render(request, "eCom/stores_form.html", {'store': store})

        # Save the store to the database.
        store.name = name
        store.description = description
        store.save()

        messages.success(request, "Store details updated successfully.")
        return redirect(reverse("vendor_home"))

    return render(request, "eCom/stores_form.html", {'store': store})


@login_required(login_url='login')
def stores_delete(request, pk):
    '''
    View to allow the user to delete a store. This view requires the user to be
    logged in and have permission to delete stores.

    Parameters:
    - request: HTTP request object.
    - pk: Primary key for the store to be deleted.

    Returns:
    If the user does not have the required permission, the view redirects to
    the buyer home page. After successful deletion, the view redirects to the
    vendor dashboard. The initial template rendered when the view is requested
    is a confirmation of deletion page.
    '''

    # Check the user permissions.
    if not request.user.has_perm("eCom.delete_stores"):
        messages.error(request, "Access Denied: You cannot edit stores.")
        return redirect(reverse("buyer_home"))

    # Fetch the specific store details.
    store = get_object_or_404(Store, pk=pk, user=request.user)

    if request.method == "POST":
        store.delete()
        messages.success(request, "Store and content successfully deleted.")
        return redirect(reverse("vendor_home"))

    return render(request, "eCom/stores_delete.html", {'store': store})


@login_required(login_url='login')
def products_detail_vendor(request, pk):
    '''
    View of product detail for the vendor. This view requires the user to be
    logged in and have permission to add products. This view is for vendors
    specifically and allows to update or delete a product.

    Parameters:
    - request: HTTP request object.
    - pk: Primary key of the specific product.

    Returns:
    If the user does not have the required permissions, the view redirects to
    the vendor dashboard. If the product does not belong to the user, the view
    redirects to the vendor dashboard. After successful authentication the view
    renders the specific product details to the user.
    '''

    # Check user permissions.
    if not request.user.has_perm("eCom.add_products"):
        messages.error(request, "Access Denied: Cannot update products.")
        return redirect(reverse("vendor_home"))

    # Fetch the specific product details.
    product = get_object_or_404(Product, pk=pk)

    # Check if the product belongs to the current user.
    if product.vendor.user != request.user:
        messages.error(request, "Access Denied: You do not own this product.")
        return redirect(reverse("vendor_home"))

    return render(
        request,
        "eCom/products_detail_vendor.html",
        {'product': product}
    )


@login_required(login_url='login')
def products_create(request, store_pk):
    '''
    View to allow vendors to create a product. The view requires the user to be
    logged in and requires permission to add products.

    Perameters:
    - request: HTTP request object.
    - store_pk: Primary key of the specific store where the porduct is to be
      added.

    Returns:
    If the user does not have the required permission the view redirects to the
    buyer home page. If the user does not own the specific store, the view re-
    directs to the vendor dashboard. If all fields are not filled, an error is
    given to complete all fields. After successful creation, the view redirects
    to the store where the product is added. The initial template rendered is
    the product form.
    '''

    # Check user permissions
    if not request.user.has_perm("eCom.add_products"):
        messages.error(request, "Access Denied: Please register as a Vendor.")
        return redirect(reverse("buyer_home"))

    # Fetch the specific store data where the product will be added.
    store = get_object_or_404(Store, pk=store_pk)

    context = {
        'store': store,
        'product': None,
    }

    # Check if the store belongs to the current user.
    if request.user != store.user:
        messages.error(request, "Access Denied: You do not own this store.")
        return redirect(reverse("vendor_home"))

    if request.method == "POST":
        name = request.POST.get("prod_name")
        description = request.POST.get("prod_description")
        price = request.POST.get("prod_price")
        quantity = request.POST.get("prod_quantity")

        if not name or not description or not price or not quantity:
            messages.error(request, "All fields are required")
            return render(request, "eCom/products_form.html", context)

        # Convert the string quantity to an integer and check if it is a valid
        # number.
        try:
            num_price = Decimal(price)
            num_qty = int(quantity)
        except (ValueError, InvalidOperation):
            messages.error(request, "Price/Quantity must be a valid number.")
            return render(request, "eCom/products_form.html", context)

        # Create and store the new product in the database.
        new_product = Product(
            name=name,
            description=description,
            quantity=num_qty,
            price=num_price,
            vendor=store,
        )
        new_product.save()

        return redirect("stores_detail", pk=store_pk)

    return render(request, "eCom/products_form.html", context)


@login_required(login_url='login')
def products_update(request, pk):
    '''
    View to allow the user to make changes to a product. The view requeres the
    user to be logged in and requires permission to change products.

    Parameters:
    - request: HTTP request object.
    - pk: Primary key of specific product.

    Returns:
    IF the user does not have the required permissions, the view redirects to
    the buyer home page. If the product does not belong to the user, the view
    redirects to the vendor dashboard. All fields needs to be completed. Once
    the product is successfully updated, the view redirects to the specific
    store where the product is added to. The initial template rendered is the
    product form with the product details already displayed.
    '''

    # Check user permissions.
    if not request.user.has_perm("eCom.change_products"):
        messages.error(request, "Access Denied: Please register as a Vendor.")
        return redirect(reverse("buyer_home"))

    # Fetch the specific product details.
    product = get_object_or_404(Product, pk=pk)

    context = {
        'product': product,
        'store': product.vendor,
    }

    # Check of the product belongs to the user.
    if product.vendor.user != request.user:
        messages.error(request, "Access Denied: You do not own this product")
        return redirect(reverse("vendor_home"))

    if request.method == "POST":
        name = request.POST.get("prod_name")
        description = request.POST.get("prod_description")
        price = request.POST.get("prod_price")
        quantity = request.POST.get("prod_quantity")

        if not name or not description or not price or not quantity:
            messages.error(request, "All fields are required.")
            return render(request, "eCom/products_form.html", context)

        # If a change in quantity is made, convert the value to integer and
        # check if it is a valid number.
        try:
            num_price = Decimal(price)
            num_qty = int(quantity)
        except (ValueError, InvalidOperation):
            messages.error(request, "Price/Quantity must be a valid number.")
            return render(request, "eCom/products_form.html", context)

        # Store the updated information to the product database.
        product.name = name
        product.description = description
        product.price = num_price
        product.quantity = num_qty
        product.save()

        return redirect("stores_detail", pk=product.vendor_id)

    return render(request, "eCom/products_form.html", context)


@login_required(login_url='login')
def products_delete(request, pk):
    '''
    View to allow a user to delete a specific product. The view requires the
    user to be logged in and permission to delete products.

    Parameters:
    - request: HTTP request object.
    - pk: Primary key of the product to be deleted.

    Returns:
    If the user does not have the required permissions the view redirects to
    the byuer home page. IF the product does not belong to the user, the view
    redirects to the vendor dashboard. On successfull deletion the view re-
    directs to the vendor dashboard. The initial view rendered is a deletion
    confirmation page.
    '''

    # Check the user permissions.
    if not request.user.has_perm("eCom.delete_products"):
        messages.error(request, "Access Denied: You cannot change products.")
        return redirect(reverse("buyer_home"))

    # Fetch the specific product details.
    product = get_object_or_404(Product, pk=pk)

    # Check if the product belongs to the current user.
    if product.vendor.user != request.user:
        messages.error(request, "Access Denied: You do not own this product.")
        return redirect(reverse("vendor_home"))

    if request.method == "POST":
        store_pk = product.vendor_id
        product.delete()

        return redirect("stores_detail", pk=store_pk)

    return render(request, "eCom/products_delete.html", {'product': product})


@login_required(login_url='login')
def buyer_home(request):
    '''
    View to show the buyer home page. All products created from all stores are
    displayed with this view. The view requirers the user to be logged in and
    have permission to view products.

    Parameters:
    - request: HTTP request object.

    Returns:
    If the user does not have the required permissions, the view redirects to
    the vendor home page. The rendered template is the buyer home page with all
    the products displayed.
    '''

    # Check user permissions.
    if not request.user.has_perm("eCom.view_products"):
        messages.error(request, "Access Denied: Please register as a Buyer.")
        return redirect(reverse('vendor_home'))

    # Fetch all the products from the database.
    products = Product.objects.all()

    return render(request, 'eCom/buyer_home.html', {'products': products})


@login_required(login_url='login')
def products_detail_buyer(request, pk):
    '''
    View to show a specific product details. The view requires the user to be
    logged in and have permission to view products. This is different from the
    product_detail_vendor view as this allows the user to add a product to
    thier cart or to review the product. To prevent a user from adding more
    than one review the view evaluates if a review exists for the current user
    on the current product.

    Parameters:
    - request: HTTP request object.
    - pk: Primary key of the specific product.

    Returns:
    If the user does not have the required permission, the view redirects to
    the login page. The rendered template is the details of the selected
    product.
    '''

    # Check user permissions.
    if not request.user.has_perm("eCom.view_products"):
        messages.error(request, "Access Denied: Cannot view products.")
        return redirect(reverse("login"))

    # Fetch the specific product details
    product = get_object_or_404(Product, pk=pk)

    # Check if the user already reviewed the product.
    reviewed = Review.objects.filter(
        product=product,
        user=request.user,
    ).exists()

    context = {'product': product, 'reviewed': reviewed}

    return render(request, "eCom/products_detail_buyer.html", context)


@login_required(login_url='login')
def add_to_cart(request, prod_pk):
    '''
    View to add products to a users cart. The view requires the user to be
    logged in. This view does not store anything to the database but creates a
    cart in the session. While the user is logged into the current session, the
    cart will remain active with the items added already and new items to be
    added. Once the session is terminated, the cart also be terminated.

    Parameters:
    - request: HTTP request object.
    - prod_pk: Primary key of the product to be added to the cart.

    Returns:
    The default quantity is 1 but if the user accidentally removes it before
    adding a new quantity, the view will generate an error requiring a quantity
    with the product detail still displayed. After successful adding, the view
    redirects to the user's cart.
    '''

    quantity = request.POST.get("quantity")

    # Check if the quantity is added.
    if not quantity:
        messages.error(request, "Please add a quantity.")
        return redirect("products_detail_buyer", pk=prod_pk)

    # Convert the quantity to an integer and default to 1 if the value is
    # incorrect or less than 1.
    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1

    except ValueError:
        quantity = 1

    # Create or fetch the cart in the session and add items.
    cart = request.session.get('cart', {})
    item = str(prod_pk)
    if item in cart:
        cart[item] += quantity
    else:
        cart[item] = quantity

    # Ensure to state the session is modified to update the cart.
    request.session['cart'] = cart
    request.session.modified = True
    return redirect("user_cart")


def retrieve_products(request):
    '''
    Function used within the user_cart view to retreive the products stored in
    the current session cart object.

    Parameters:
    - request: HTTP request object.

    Returns:
    Returns a list of product details stored in the session cart.
    '''

    # Create an empty products list and request the current session.
    products = []
    session = request.session

    # Check if there is a cart in the session and append the products list with
    # the cart items.
    if "cart" in session:
        for pk, quantity in session["cart"].items():
            try:
                product = Product.objects.get(pk=pk)
                products.append({'product': product, 'quantity': quantity})
            except Product.DoesNotExist:
                pass

    return products


@login_required(login_url='login')
def user_cart(request):
    '''
    View to allow a user to view their cart. The view requires the user to be
    logged in.

    Parameters:
    - request: HTTP request object.

    Returns:
    If the user has items in his cart, the view renders the cart items and the
    total cost, else it renders a message to state an empty cart.
    '''

    # Retreive the items from the session cart.
    cart = retrieve_products(request)

    # Initialise the price variables.
    total_price = 0

    # Each cart item populates and calculates the subtotal and grand total.
    for item in cart:
        item['subtotal'] = item['product'].price * item['quantity']
        total_price += item['subtotal']

    context = {
        'cart': cart,
        'total_price': total_price,
    }

    return render(request, "eCom/user_cart.html", context)


def clear_cart(request):
    '''
    View to clear the users cart.

    Parameters:
    - request: HTTP request object.

    Returns:
    Renders the user cart view with the message of an empty cart.
    '''

    # Clears the current session cart and modifies the session to update.
    request.session['cart'] = {}
    request.session.modified = True

    return render(request, "eCom/user_cart.html")


@login_required(login_url='login')
def check_out(request):
    '''
    View to allow the user to check out the current products in their cart. The
    view requires the user to be logged in. The view also checks specific
    product quantities and generates an error if the required quantity is more
    than the available quantity. The product quantity is also updated to the
    datebase reducing the quantity accordingly after check out. The view
    generates an invoice using a template and emails the invoice to the current
    user.

    Parameters:
    - request: HTTP request object.

    Returns:
    If the cart is empty, the view redirects to the cart view with and empty
    cart message.
    '''

    # Fetch the cart from the current session if it exists.
    cart = retrieve_products(request)
    if not cart:
        return redirect("user_cart")

    # This loop checks the quantity againt the available product quantity and
    # also updates the product quantity after check out to the database.
    with transaction.atomic():

        # Creates an order using the Order model ans saves it to the database.
        order = Order.objects.create(user=request.user)
        total_price = 0

        for item in cart:
            product = item['product']
            quantity = item['quantity']
            price = product.price

            if product.quantity < quantity:
                messages.error(
                    request,
                    "Product stock is less than required quantity."
                )
                return redirect("user_cart")

            product.quantity -= quantity
            product.save()

            subtotal = price * quantity
            total_price += subtotal

            # Creates an order item using OrderItem model and saves it to the
            # database. This item is used to store products that the user has
            # purchased.
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price=price,
                quantity=quantity,
                subtotal=subtotal
            )

        order.total_price = total_price
        order.save()

    # Generates the invoice email using build_invoice_email() from the utils
    # module and sends the email.
    email = build_invoice_email(request.user, order)
    email.send()

    # Clears the cart after checkout and updates the session.
    request.session['cart'] = {}
    request.session.modified = True

    context = {'order': order}

    return render(request, "eCom/order_confirmation.html", context)


@login_required(login_url='login')
def add_review(request, pk):
    '''
    View to allow the user to post a review for a product. This view requires
    the user to be logged in. Checks the OrderItem data in the database to
    evaluate if the user already purchased the product and if so, confirms that
    the view is a verified review, else the review is unverified.

    Parameters:
    - request: HTTP request object.
    - pk: Primary key of the specific product to be reviewed.

    Returns:
    If the user is not a buyer, the view redirects to the vendor dashboard. If
    the user has already reviewed the product, an error is generated to warn
    the user that they already reviewed the product. All fields are required.
    If the review is created, the view redirects to the product detail page.
    The initial rendered template is the review form.
    '''

    # Check if user is a buyer.
    if not request.user.groups.filter(name="Buyer").exists():
        messages.error(request, "Access Denied: You are not a Buyer.")
        return redirect(reverse("vendor_home"))

    # Fetch the specific product and user.
    product = get_object_or_404(Product, pk=pk)
    user = request.user

    # Check if the user already purchased the product.
    verified = OrderItem.objects.filter(
        product=product,
        order__user=user
    ).exists()

    # Check if the user already reviewed this product.
    reviewed = Review.objects.filter(product=product, user=user).exists()

    context = {
        "product": product,
        "user": user,
        "verified": verified,
        "reviewed": reviewed,
    }

    if reviewed:
        messages.error(request, "You already reviewed this product.")
        return redirect("products_detail_buyer", pk=pk)

    if request.method == "POST":
        title = request.POST.get("title")
        comments = request.POST.get("comments")
        rating = request.POST.get("rating")

        if not title or not comments or not rating:
            messages.error(request, "All fields are required.")
            return render(request, "eCom/review_form.html", context)

        # Convert the rating into an integer and evaluate the correct value.
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Rating must be 1-5.")
            return render(request, "eCom/review_form.html", context)

        # Create the new review using the Review model.
        new_review = Review.objects.create(
            user=user,
            product=product,
            title=title,
            comments=comments,
            rating=rating,
            is_verified=verified,
        )

        messages.success(request, "Review posted successfully.")
        return redirect("products_detail_buyer", pk=pk)

    return render(request, "eCom/review_form.html", context)


def welcome_view(request):
    '''
    View to show the welcome page for registration or login.

    Parameters:
    - request: HTTP request object.

    Returns:
    Renders the welcome page.
    '''
    return render(request, 'eCom/welcome.html')


'''
The views below are for API endpoints.
'''


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user_api(request):
    serializer = RegisterUserSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()

        return Response(
            {'message': 'User registered.'},
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BasicAuthentication])
def stores_create_api(request):

    if not request.user.has_perm("eCom.add_stores"):
        return Response(
            {'error': 'You do not have permission to add stores'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = StoreSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(user=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BasicAuthentication])
def add_product_api(request, store_id):

    if not request.user.has_perm('eCom.add_products'):
        return Response(
            {'error': 'You cannot add products.'},
            status=status.HTTP_403_FORBIDDEN
        )

    store = get_object_or_404(Store, pk=store_id)

    if store.user_id != request.user.id:
        return Response(
            {'error': 'You do not own this store'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ProductSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(vendor=store)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([BasicAuthentication])
def retrieve_reviews_api(request):

    if not request.user.groups.filter(name='Vendor').exists():
        return Response(
            {'error': 'You are not a vendor.'},
            status=status.HTTP_403_FORBIDDEN
        )

    reviews = Review.objects.filter(
        product__vendor__user=request.user
    ).select_related(
        "product",
        "product__vendor",
        "product__vendor__user"
    )

    serializer = ReviewSerializer(reviews, many=True)

    return Response(
        serializer.data,
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([BasicAuthentication])
def retrieve_stores_products_api(request):
    if not request.user.groups.filter(name__in=['Vendor', 'Buyer']).exists():
        return Response(
            {'error': 'Access denied. Please register.'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = StoreSerializer(Store.objects.all(), many=True)

    return Response(
        serializer.data,
        status=status.HTTP_200_OK
    )
