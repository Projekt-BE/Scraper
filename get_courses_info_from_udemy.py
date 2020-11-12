import argparse
import csv
import os
import shutil
import time

import requests
import validators
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
IMAGES_PATH = os.path.join(SCRIPT_PATH, "img")
COURSES_CSV_NAME = os.path.join(SCRIPT_PATH, "courses.csv")
CATEGORIES_CSV_NAME = os.path.join(SCRIPT_PATH, "categories.csv")
COURSE_HEADERS = ['title', 'description', 'author', 'duration', 'rating', 'price', 'image_name', 'category', 'subcategory']
CATEGORIES_HEADERS = ['category', 'subcategory']
DEFAULT_WEBSITE_URL = "https://www.udemy.com/courses/development"
DEFAULT_AMOUNT_OF_COURSES = 16

WEBSITE_LOADING_TIMEOUT = 20
SCROLL_DELAY = 0.05


def scroll_to_top(driver):
    driver.execute_script(f"window.scrollTo(0,0)")


def scroll_to_bottom(driver, delay=0.1):
    scroll_offset = driver.execute_script("return window.scrollY")
    while True:
        driver.execute_script("window.scrollBy(0,screen.height)")
        time.sleep(delay)
        last_scroll_offset = scroll_offset
        scroll_offset = driver.execute_script("return window.scrollY")
        if last_scroll_offset == scroll_offset:
            break


def download_image(image_url, path):
    image_url = image_url.replace('240x135', '480x270')
    image_name = os.path.basename(image_url)
    img_data = requests.get(image_url).content
    with open(os.path.join(path, image_name), 'wb') as handler:
        handler.write(img_data)
    return image_name


def get_course_category(driver, course_url):
    driver.execute_script("window.open('');")

    driver.switch_to.window(driver.window_handles[1])
    driver.get(course_url)
    try:
        menu = WebDriverWait(driver, WEBSITE_LOADING_TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.topic-menu.udlite-breadcrumb")))
    except TimeoutException:
        print(f"Timeout occurred. Website loading time exceeded {WEBSITE_LOADING_TIMEOUT}s")
        print(f"Skipping this course")
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return None, None
    categories = menu.find_elements_by_css_selector('a.udlite-heading-sm')
    category = categories[0].text
    subcategory = categories[1].text

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return category, subcategory


def get_course_data(driver, course):
    course_url = course.find_element_by_css_selector("a.udlite-custom-focus-visible.browse-course-card--link--3KIkQ") \
        .get_attribute("href")

    category, subcategory = get_course_category(driver, course_url)
    if not category:
        return None
    title = course.find_element_by_css_selector("div.course-card--course-title--2f7tE").text
    description = course.find_element_by_css_selector("p.course-card--course-headline--yIrRk").text
    author = course.find_element_by_css_selector("div.course-card--instructor-list--lIA4f").text
    duration = course.find_element_by_css_selector("span.course-card--row--1OMjg").text.replace("total hours", "godzin")
    image_url = course.find_element_by_css_selector("img.course-card--course-image--2sjYP").get_attribute("src")
    price = course.find_elements_by_css_selector(
        "div.price-text--price-part--Tu6MH.course-card--discount-price--3TaBk.udlite-heading-md span span")
    if len(price) == 0:
        print('Free course. Skipping.')
        return None
    price = price[0].text
    duration = duration.split(' ')[0]
    price = price.split(' ')[0].replace(',', '.')

    # Rating is not always present
    ratings = course.find_elements_by_css_selector("span.udlite-heading-sm.star-rating--rating-number--3lVe8")
    rating = ratings[0].text if len(ratings) > 0 else None

    # As long as image src is not loaded on the website, try to scroll through website
    while not validators.url(image_url):
        scroll_to_top(driver)
        scroll_to_bottom(driver, SCROLL_DELAY * 10)
        image_url = course.find_element_by_css_selector("img.course-card--course-image--2sjYP").get_attribute("src")

    image_url = image_url.split('?', 1)[0]
    image_name = download_image(image_url, IMAGES_PATH)

    return [title, description, author, duration, rating, price, image_name, category, subcategory]


def get_courses_from_page(driver, url, page):
    # Load website
    driver.get(f"{url}/?p={page}")

    try:
        courses = WebDriverWait(driver, WEBSITE_LOADING_TIMEOUT).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR,
                                                   "div.course-list--container--3zXPS div.popper--popper--19faV.popper--popper-hover--4YJ5J"))
        )
    except TimeoutException:
        driver.quit()
        print(f"Timeout occurred. Website loading time exceeded {WEBSITE_LOADING_TIMEOUT}s")
        return

    scroll_to_bottom(driver)
    result = []
    for i, c in enumerate(courses):
        course = get_course_data(driver, c)
        if course is not None:
            result.append(course)

    # courses = [get_course_data(driver, c) for c in courses]
    return result


def get_courses(amount, url):
    driver = webdriver.Firefox()
    courses = []
    current_page = 1
    while len(courses) < amount:
        print(f'Page #{current_page} is being processed...')
        courses.extend(get_courses_from_page(driver, url, current_page))
        current_page += 1

    driver.quit()
    return courses


def get_used_categories_from_course_list(courses):
    categories = set([(c[7], c[8]) for c in courses])
    return categories


def prepare_csv_file(filename, headers):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';', quotechar='\"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)


def save_data_to_csv(filename, data):
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';', quotechar='\"', quoting=csv.QUOTE_MINIMAL)
        for c in data:
            writer.writerow(c)


def save_courses_from_url(url, amount):
    print(f'Scrapping courses from: {url}')
    courses = get_courses(amount, url)
    categories = get_used_categories_from_course_list(courses)
    print('Saving to files...')
    save_data_to_csv(COURSES_CSV_NAME, courses)
    save_data_to_csv(CATEGORIES_CSV_NAME, categories)


def main():
    prepare_csv_file(COURSES_CSV_NAME, COURSE_HEADERS)
    prepare_csv_file(CATEGORIES_CSV_NAME, CATEGORIES_HEADERS)

    # Clear destination directory for images
    if os.path.exists(IMAGES_PATH):
        shutil.rmtree(IMAGES_PATH)
    os.mkdir(IMAGES_PATH)

    save_courses_from_url("https://www.udemy.com/courses/development", 256)
    save_courses_from_url("https://www.udemy.com/courses/design", 64)
    save_courses_from_url("https://www.udemy.com/courses/business", 64)
    save_courses_from_url("https://www.udemy.com/courses/personal-development", 64)
    save_courses_from_url("https://www.udemy.com/courses/it-and-software", 64)

    print('All done.')


if __name__ == '__main__':
    main()
