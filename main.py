import csv
import os
import shutil
import time

import requests
import validators
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
IMAGES_PATH = os.path.join(SCRIPT_PATH, "img")
RESULT_CSV_NAME = os.path.join(SCRIPT_PATH, "courses.csv")
WEBSITE_URL = "https://www.udemy.com/courses/development/?p="
MIN_AMOUNT_OF_COURSES = 100


def scroll_to_top(driver):
    driver.execute_script(f"window.scrollTo(0,0)")


def scroll_to_bottom(driver, delay):
    scroll_offset = driver.execute_script("return window.scrollY")
    while True:
        driver.execute_script(f"window.scrollBy(0,screen.height)")
        time.sleep(delay)
        last_scroll_offset = scroll_offset
        scroll_offset = driver.execute_script("return window.scrollY")
        if last_scroll_offset == scroll_offset:
            break


def get_course_data(driver, course):
    title = course.find_element_by_css_selector("div.course-card--course-title--2f7tE").text
    description = course.find_element_by_css_selector("p.course-card--course-headline--yIrRk").text
    author = course.find_element_by_css_selector("div.course-card--instructor-list--lIA4f").text
    length = course.find_element_by_css_selector("span.course-card--row--1OMjg").text.replace("total hours", "godzin")
    rating = course.find_element_by_css_selector("span.udlite-heading-sm.star-rating--rating-number--3lVe8").text
    image_url = course.find_element_by_css_selector("img.course-card--course-image--2sjYP").get_attribute("src")
    price = course.find_element_by_css_selector(
        "div.price-text--price-part--Tu6MH.course-card--discount-price--3TaBk.udlite-heading-md span span").text

    while not validators.url(image_url):
        scroll_to_top(driver)
        scroll_to_bottom(driver, 1)
        image_url = course.find_element_by_css_selector("img.course-card--course-image--2sjYP").get_attribute("src")

    image_url = image_url.split('?', 1)[0]
    image_name = os.path.basename(image_url)
    img_data = requests.get(image_url).content
    with open(os.path.join(IMAGES_PATH, image_name), 'wb') as handler:
        handler.write(img_data)
    return [title, description, author, length, rating, price, image_name]


def get_courses_from_url(driver, url):
    if not os.path.isdir(IMAGES_PATH):
        os.mkdir(IMAGES_PATH)
    driver.get(url)

    try:
        courses = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR,
                                                   "div.course-card--container--3w8Zm.course-card--large--1BVxY"))
        )
    except:
        driver.quit()
        print("ERROR")
        return

    scroll_to_bottom(driver, 0.1)
    courses = [get_course_data(driver, c) for c in courses]
    return courses


def get_courses(amount):
    driver = webdriver.Chrome(executable_path="/home/jedrek/Documents/chromedriver")
    courses = []
    current_page = 1
    while len(courses) < amount:
        courses.extend(get_courses_from_url(driver, f'{WEBSITE_URL}{current_page}'))
        current_page += 1

    driver.quit()
    return courses


def main():
    # Clear destination directory for images
    if os.path.exists(IMAGES_PATH):
        shutil.rmtree(IMAGES_PATH)

    courses = get_courses(MIN_AMOUNT_OF_COURSES)

    with open(RESULT_CSV_NAME, 'w', newline='') as file:
        writer = csv.writer(file, delimiter=';', quotechar='\"', quoting=csv.QUOTE_MINIMAL)
        for c in courses:
            writer.writerow(c)

    print()


if __name__ == '__main__':
    main()
