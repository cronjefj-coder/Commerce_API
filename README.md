# Commerce eCom Application
## Getting Started

This document provides guidance on how to setup and run Commerce.

## Prerequisites

Python 3.11 is required to be installed on your system.

## Local setup

Take note that this setup is for a Windows operating system using command prompt. If you have a MacOS or Linux setup, the commands will differ. Please refer to MacOS or Linux terminal documentation for equivalent commands. Clone the github repository for the application.

1. **Setup an isolated Python virtual environment:**

To setup a virtual environment on your system, use the following command in command prompt.
```pip -m venv env_name```.

To activate the environment,  run ```env_name\Scripts\activate```. Ensure that you are within the directory where the environment was created.

2. **Upgrade pip and install project dependencies:**

Make sure you have the latest pip version by running ```python -m pip install --upgrade pip```.

Run the following command for project dependencies: ```python -m pip install -r requirements.txt```

3. **Database update:**

Run ```python manage.py migrate``` to ensure the database is up to date.

4. **Group setup:**

After you have updated the database, run ```python manage.py setup_group``` to create and setup the groups and permissions.

5. **Admin superuser:**

If you want access to the Django administration section of the application, you will have to create an admin superuser by running ```python manage.py createsuperuser```.

6. **Run the application:**

To run the application use the command ```python manage.py runserver```. This will start the local server http://127.0.0.1:8000/. You can open your preferred browser and navigate to the server url. NOTE to access Django admin, add 'admin/' to the back of the server url.

## Application Features:

When you have navigated to the server url, the application will a Welcome page that allows you to register or login. 

1. **Registration**

You can register as either a Vendor or a Buyer. After successful registration, you will be automatically logged in and redirected to the relevant home page depending on your choice of Vendor or Buyer. Note that if you want to register as both a Vendor and Buyer, you will have to use different usernames and register separately.

3. **Forgot password**

You will have the ability to reset your password once you have registered. To reset a password, simply click on the Forgot Password link in the login screen. Note that you will only have 10 minutes to reset your password. After the 10 minutes, you will have to follow the Forgot Password link again if you want to reset the password.

2. **Vendors**

As a Vendor, you will be able to create, edit and delete stores. Within the stores, you will be able to create, edit and delete products that can be sold. Be sure to visit your stores frequently to monitor product stock levels as this will automatically decrease as buyers purchase your products. To view or edit your stores and products, simply click on the store or product title.

3. **Buyers**

As a Buyer, you will be able to see all products sold from all stores. To purchase a product, simply click on the product title. You will be redirected to the product details where you can either leave a review or add the product to your cart. You can only leave one review per product. Take note that your cart is only populated while you are logged in. As soon as you have logged out, the items not purchased will disappear from your cart. Once you have checked out, you will receive an invoice via email.

## API endpoints:

The application also includes API endpoints for some of the features. Please note that POSTMAN was used to test the endpoints. JSON was used as the data format for the API's. The following features are configured as endpoints.

1. **User Registration**

To test the endpoints you will have to register as a user and choose a group (Vendor or Buyer). If you have already registered accounts on the application (for both vendor and buyer) you can use the cridentials in the authentication tab in POSTMAN to authenticate yourself. Please choose basic authentication as the method in POSTMAN. 

If you have not yet registered an account, use a ```POST``` command with the following url ```127.0.0.1:8000/api/register/``` and the following raw command in the Body tab:

```{"username": "Your username", "email": "your email", "password": "password", "conf_pword": "password",  "role_id": "Vendor" or "Buyer"}```

Once you send, you should recveive a response that you are successfully registered.

2. **Create Store**

This is only allowed if you have registered and authenticated yourself as a vendor. Use a ```POST``` command with the following url ```127.0.0.1:8000/api/stores/create/``` and enter the following attributes in the same ```JSON``` syntax used in the register field. ```"name"``` and ```"description"```.

3. **Add Product**

This is only allowed if you have registered and authenticated yourself as a vendor. Use a ```POST``` command and the following url ```127.0.0.1:8000/api/<int:store_id>/product/add/```. Note that a vendor must own the store to create a product in it. To get your ```store_id```, run the View stores and products command (see 4 below). Enter the following attributes in the same ```JSON``` syntax used in the register field. ```"name"```,```"description"```, ```quantity``` and ```price```.

4. **View Stores and Products**

This is allowed for both Vendors and Buyers but you still have to be a registered user thus your cridentials still needs to be added to the authentication tab. Use a ```GET``` command with the following url ```127.0.0.1:8000/api/stores_products/view/```.

5. **Retrieve Reviews**

This is only allowed for vendors. Use a ```GET``` command with the url ```127.0.0.1:8000/api/reviews/```. You will only be able to view reviews of products in your own stores that you created.

## After app usage:

Do take note that after you have used the application and closed your browser, the server must be stopped. Within the command prompt terminal, navigate to the bottom and press CTRL-C to stop the server.

Also note to deactivate your virtual environment when you are done with the application. In the command prompt terminal, type ```deactivate``` and the virtual environment will be deactivated.
