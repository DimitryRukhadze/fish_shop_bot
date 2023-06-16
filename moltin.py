import requests


def get_access_token(client_id, client_secret):

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }

    response = requests.post(
        'https://api.moltin.com/oauth/access_token',
        data=data
    )
    response.raise_for_status()

    response_from_json = response.json()

    return response_from_json['access_token']


def get_all_products(token):

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(
        'https://api.moltin.com/catalog/products',
        headers=headers
    )
    response.raise_for_status()

    return response.json()


def get_product_by_id(token, id):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    product_url = f'https://api.moltin.com/catalog/products/{id}'
    response = requests.get(product_url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_product_inventory(token, product_id):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    product_inv_url = f'https://api.moltin.com/v2/inventories/{product_id}'

    response = requests.get(product_inv_url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_product_image_url(token, product_id):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    product_img_inf_url = f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image'
    response = requests.get(product_img_inf_url, headers=headers)
    response.raise_for_status()

    image_id = response.json()['data']['id']

    image_data_url = f'https://api.moltin.com/v2/files/{image_id}'

    response = requests.get(image_data_url, headers=headers)
    response.raise_for_status()

    return response.json()['data']['link']['href']


def create_customer(auth_token, name, email):
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'type': 'customer',
            'name': str(name),
            'email': email,
        }
    }

    response = requests.post(
        'https://api.moltin.com/v2/customers',
        headers=headers,
        json=json_data
    )
    response.raise_for_status()

    return response.json()


def get_customer_by_name(name, auth_token):
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    params = {
        'filter': f'eq(name,{name})',
    }

    response = requests.get(
        'https://api.moltin.com/v2/customers',
        headers=headers,
        params=params
    )
    response.raise_for_status()

    return response.json()


def create_cart(auth_token):
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    data = {
        'data': {
            'name': 'new_cart'
        }
    }

    response = requests.post(
        'https://api.moltin.com/v2/carts',
        headers=headers,
        json=data
    )
    response.raise_for_status()

    return response.json()


def get_cart_items(auth_token, cart_id):

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    response = requests.get(
        f'https://api.moltin.com/v2/carts/{cart_id}/items',
        headers=headers
    )
    response.raise_for_status()

    return response.json()


def get_cart(auth_token, cart_id):
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    response = requests.get(
        f'https://api.moltin.com/v2/carts/{cart_id}',
        headers=headers
    )
    response.raise_for_status()

    return response.json()


def add_product_to_cart(auth_token, cart_id, product_id, quantity=1):
    cart_url = f'https://api.moltin.com/v2/carts/{cart_id}/items'

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
        'X-MOLTIN-CURRENCY': 'USD'
    }

    data = {
        'data': {
            'quantity': quantity,
            'type': 'cart_item',
            'id': product_id
        }
    }

    resp = requests.post(cart_url, headers=headers, json=data)
    resp.raise_for_status()


def delete_item_from_cart(auth_token, cart_id, product_id):

    del_item_url = f'https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}'

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    resp = requests.delete(del_item_url, headers=headers)
    resp.raise_for_status()
