import argparse
import csv
import io
import os

import unidecode
from prestapyt.prestapyt import PrestaShopWebServiceDict

FEATURES = {'Author': '5',
            'Rating': '6',
            'Duration': '7'}

available_feature_values = {FEATURES[key]: [] for key in FEATURES}


def remove_accented_characters(text):
    return unidecode.unidecode(text)


def get_dict_list_from_csv(filename):
    with open(filename, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';', quotechar='\"')
        dict_list = []
        for line in reader:

            dict_list.append(line)
    return dict_list


def remove_old_data(prestashop):
    # Remove categories
    all_categories = prestashop.get('categories')['categories']['category']
    categories_to_delete = [c['attrs']['id'] for c in all_categories if int(c['attrs']['id']) > 2]
    if len(categories_to_delete):
        prestashop.delete('categories', resource_ids=categories_to_delete)

    # Remove products
    all_products = prestashop.get('products')['products']
    if all_products:
        products_to_delete = [p['attrs']['id'] for p in all_products['product']] \
            if type(all_products['product']) is list \
            else [all_products['product']['attrs']['id']]
        prestashop.delete('products', resource_ids=products_to_delete)

    # Remove combinations
    all_combinations = prestashop.get('combinations')['combinations']
    if all_combinations:
        combinations_to_delete = [p['attrs']['id'] for p in all_combinations['combination']]
        prestashop.delete('combinations', resource_ids=combinations_to_delete)

    # Remove feature values
    all_feature_values = prestashop.get('product_feature_values')['product_feature_values']
    if all_feature_values:
        feature_values_to_delete = [f['attrs']['id'] for f in all_feature_values['product_feature_value']] \
            if type(all_feature_values['product_feature_value']) is list \
            else [all_feature_values['product_feature_value']['attrs']['id']]
        prestashop.delete('product_feature_values', resource_ids=feature_values_to_delete)

    # # Remove features
    # all_features = prestashop.get('product_features')['product_features']
    # if all_features:
    #     features_to_delete = [f['attrs']['id'] for f in all_features['product_feature']]
    #     prestashop.delete('product_features', resource_ids=features_to_delete)


def create_category(category_name, parent_id, blank_category, prestashop):
    category_link = remove_accented_characters(category_name.lower().replace(' ', '-'))
    new_category = dict(blank_category)
    new_category['category']['active'] = '1'
    new_category['category']['id_shop_default'] = '1'
    new_category['category']['name']['language']['value'] = category_name
    new_category['category']['id_parent'] = parent_id
    new_category['category']['link_rewrite']['language']['value'] = category_link
    return prestashop.add('categories', new_category)


def import_categories(categories, prestashop):
    remove_old_data(prestashop)
    blank_category = prestashop.get('categories', options={'schema': 'blank'})
    categories_dict = {}
    category_ids = {}
    for c in categories:
        if categories_dict.get(c['category']):
            categories_dict[c['category']].append(c['subcategory'])
        else:
            categories_dict[c['category']] = [c['subcategory']]

    for main_category, subcategories in categories_dict.items():
        created_category = create_category(main_category, 2, blank_category, prestashop)
        main_category_id = created_category['prestashop']['category']['id']
        category_ids[main_category] = main_category_id
        for subcategory in subcategories:
            created_subcategory = create_category(subcategory, main_category_id, blank_category, prestashop)
            category_ids[subcategory] = created_subcategory['prestashop']['category']['id']

    return category_ids


def get_feature(value, feature_id, prestashop):
    all_feature_values = prestashop.get('product_feature_values')['product_feature_values']['product_feature_value']
    all_feature_values_id = [f['attrs']['id'] for f in all_feature_values]

    for value_id in all_feature_values_id:
        feature_value_dict = prestashop.get('product_feature_values', value_id)
        feature_id = feature_value_dict['product_feature_value']['id_feature']
        feature_value = feature_value_dict['product_feature_value']['value']['language']['value']
        if value == str(feature_value) and feature_id == str(feature_id):
            return feature_value_dict
    return None


def get_feature_value_id(value, feature_name, prestashop):
    feature_id = str(FEATURES[feature_name])

    # Check if feature value exists already
    for feature_value_dict in available_feature_values.get(feature_id, []):
        if feature_value_dict['value'] == value:
            return feature_value_dict['id']  # Return id if feature exists

    # Create new feature value
    new_feature = prestashop.get('product_feature_values', options={'schema': 'blank'})
    new_feature['product_feature_value']['id_feature'] = feature_id
    new_feature['product_feature_value']['value']['language']['value'] = value
    result = prestashop.add('product_feature_values', new_feature)
    new_feature_id = result['prestashop']['product_feature_value']['id']
    new_feature_value = result['prestashop']['product_feature_value']['value']['language']['value']

    available_feature_values[feature_id].append({'value': new_feature_value, 'id': new_feature_id})

    return new_feature_id


def upload_image(product_id, image_name, prestashop):
    image_path = os.path.join('img', image_name)
    fd = io.open(image_path, "rb")
    content = fd.read()
    result = prestashop.add(f'/images/products/{product_id}', files=[('image', image_name, content)])
    # print(result)


def set_stock_quantity(stock_id, quantity, prestashop):
    stock = prestashop.get('stock_availables', stock_id)
    stock['stock_available']['quantity'] = quantity
    prestashop.edit('stock_availables', stock)


def create_product(title, description, price, category, subcategory, duration, author, rating, blank_product,
                   prestashop):
    new_product = dict(blank_product)

    title = title.replace('C#', 'C-Sharp').replace('#', '')

    product_features = [
        {'id': FEATURES['Duration'], 'id_feature_value': get_feature_value_id(duration + ' godz.', 'Duration', prestashop)},
        {'id': FEATURES['Author'], 'id_feature_value': get_feature_value_id(author, 'Author', prestashop)}
    ]
    if rating:
        product_features.append({'id': FEATURES['Rating'],
                                 'id_feature_value': get_feature_value_id(rating + '/5,0', 'Rating', prestashop)})

    new_product['product']["id_category_default"] = subcategory
    new_product['product']["associations"]["categories"]["category"] = [{'id': category}, {'id': subcategory}]
    new_product['product']["associations"]["product_features"]["product_feature"] = product_features
    new_product['product']["name"]["language"]["value"] = title
    new_product['product']["description"]["language"]["value"] = description
    new_product['product']["price"] = price

    new_product['product']["available_for_order"] = '1'
    new_product['product']["show_price"] = '1'
    new_product['product']["id_tax_rules_group"] = '1'
    new_product['product']["indexed"] = '1'
    new_product['product']["type"] = "simple"
    new_product['product']["minimal_quantity"] = '1'
    new_product['product']["visibility"] = 'both'
    new_product['product']["id_shop_default"] = '1'
    new_product['product']["active"] = '1'
    new_product['product']["condition"] = "new"
    new_product['product']["pack_stock_type"] = '3'
    new_product['product']["state"] = '1'
    return prestashop.add('products', new_product)


def import_products(products, category_ids, prestashop):
    blank_product = prestashop.get('products', options={'schema': 'blank'})
    for i, p in enumerate(products):
        created_product = create_product(p['title'], p['description'], p['price'], category_ids[p['category']],
                                         category_ids[p['subcategory']], p['duration'], p['author'], p['rating'],
                                         blank_product, prestashop)
        product_id = created_product['prestashop']['product']['id']
        stock_id = created_product['prestashop']['product']["associations"]["stock_availables"]['stock_available']['id']
        set_stock_quantity(stock_id, 10, prestashop)
        upload_image(product_id, p['image_name'], prestashop)
        print(f'    Product #{i} imported.')


def main(args):
    prestashop = PrestaShopWebServiceDict('http://192.168.1.164/api', args.key)

    print('Removing old data...')
    remove_old_data(prestashop)

    print('Importing categories...')
    categories = get_dict_list_from_csv('categories.csv')
    category_ids = import_categories(categories, prestashop)

    print('Importing products and images...')
    products = get_dict_list_from_csv('courses.csv')
    import_products(products, category_ids, prestashop)

    print('All done.')


def parse_args():
    parser = argparse.ArgumentParser(description='Script importing categories, courses and images to PrestaShop')
    parser.add_argument('-k', '--key', required=True, type=str, help='Key for PrestaShop webservice')
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
