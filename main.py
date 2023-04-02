import requests
import json

from environs import Env


SAMPLE_CUSTOMER = {
    'name': 'R',
    'email': 'ron@swanson.com',
    'password': 'mysecretpassword'
}

def get_access_token(client_secret):

    data = {
        'client_id': 'XMUVQxGxai0NA7pfgiejMGVdq6EZ6bnsAKS45zRDg0',
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()

    decoded_response = response.json()

    return decoded_response['access_token']


def get_all_products(token):

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    response = requests.get('https://api.moltin.com/catalog/products', headers=headers)
    response.raise_for_status()

    return response.json()


def create_customer(auth_token):
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'type': 'customer',
            'name': SAMPLE_CUSTOMER['name'],
            'email': SAMPLE_CUSTOMER['email'],
            'password': SAMPLE_CUSTOMER['password'],
        },
    }

    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=json_data)
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

    response = requests.get('https://api.moltin.com/v2/customers', headers=headers, params=params)
    response.raise_for_status()

    return response.json()


def create_cart(auth_token):
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    data = {
        'data':{
            'name':'new_cart'
        }
    }

    response = requests.post('https://api.moltin.com/v2/carts', headers=headers, json=data)

    return response.json()


def add_product_to_cart(auth_token, cart_id, product_id):
    cart_url = f'https://api.moltin.com/v2/carts/{cart_id}/items'

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }

    data = {
        'data':{
            'quantity': 1,
            'type':'cart_item',
            'id': product_id
        }
    }

    resp = requests.post(cart_url, headers=headers, json=data)
    print(resp.json())


if __name__ == '__main__':

    env = Env()
    env.read_env()
    secret_key = env('MOLTIN_SECRET_KEY')
    access_token = get_access_token(secret_key)

    all_products = get_all_products(access_token)
    all_products_ids = [
        product['id']
        for product in all_products['data']
        ]

    cart = create_cart(access_token)
    cart_id = cart['data']['id']
    print(cart)
    add_product_to_cart(access_token, cart_id, all_products_ids[0])
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    resp = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers)
    print(resp.json())
