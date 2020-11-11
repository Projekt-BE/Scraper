import argparse
import csv
import io
import os

import unidecode
from prestapyt.prestapyt import PrestaShopWebServiceDict


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
        products_to_delete = [p['attrs']['id'] for p in all_products['product']]
        prestashop.delete('products', resource_ids=products_to_delete)


def create_category(category_name, parent_id, prestashop):
    category_link = remove_accented_characters(category_name.lower().replace(' ', '-'))
    new_category = prestashop.get('categories', options={'schema': 'blank'})
    new_category['category']['active'] = '1'
    new_category['category']['id_shop_default'] = '1'
    new_category['category']['name']['language']['value'] = category_name
    new_category['category']['id_parent'] = parent_id
    new_category['category']['link_rewrite']['language']['value'] = category_link
    return prestashop.add('categories', new_category)


def import_categories(categories, prestashop):
    remove_old_data(prestashop)
    categories_dict = {}
    category_ids = {}
    for c in categories:
        if categories_dict.get(c['category']):
            categories_dict[c['category']].append(c['subcategory'])
        else:
            categories_dict[c['category']] = [c['subcategory']]

    for main_category, subcategories in categories_dict.items():
        created_category = create_category(main_category, 2, prestashop)
        main_category_id = created_category['prestashop']['category']['id']
        category_ids[main_category] = main_category_id
        for subcategory in subcategories:
            created_subcategory = create_category(subcategory, main_category_id, prestashop)
            category_ids[subcategory] = created_subcategory['prestashop']['category']['id']

    return category_ids


def upload_image(product_id, image_name, prestashop):
    image_path = os.path.join('img', image_name)
    fd = io.open(image_path, "rb")
    content = fd.read()
    result = prestashop.add(f'/images/products/{product_id}', files=[('image', image_name, content)])
    # print(result)


def create_product(title, description, price, category, subcategory, prestashop):
    new_product = prestashop.get('products', options={'schema': 'blank'})

    title = title.replace('C#', 'C-Sharp').replace('#', '')

    new_product['product']["id_category_default"] = subcategory
    new_product['product']["associations"]["categories"]["category"] = [{'id': category}, {'id': subcategory}]
    new_product['product']["name"]["language"]["value"] = title
    new_product['product']["description"]["language"]["value"] = description
    new_product['product']["price"] = price

    new_product['product']["cache_has_attachments"] = '1'
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
    for p in products:
        created_product = create_product(p['title'], p['description'], p['price'], category_ids[p['category']],
                                         category_ids[p['subcategory']], prestashop)
        product_id = created_product['prestashop']['product']['id']
        upload_image(product_id, p['image_name'], prestashop)


def main(args):
    prestashop = PrestaShopWebServiceDict('http://0976baee8833.ngrok.io/api', args.key)
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
