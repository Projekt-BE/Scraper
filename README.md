## What is it?
Pack of scripts allowing fast and automated population of PrestaShop database with categories, products and images.
Data is scrapped from www.udemy.com. Script is developed for university project.

Scripts:
* Data scrapper - `get_courses_info_from_udemy.py`
* Database population - `import_data_to_prestashop.py`

## How to execute it?

##### Python:
* Python 3.7 or newer required. 
* To install all required dependencies: `pip install -r requirements.txt`

##### WebDriver:
Script uses Firefox webdriver for automated web browsing. Path of the webdriver needs to be specified in system's PATH

#### Scripts execution:

* `python get_courses_info_from_udemy.py`
<pre>
Script scrapping www.udemy.com for ~500 courses required for University Project. 
Prepared data can be later imported with the second script.
</pre>

<br />

* `python import_data_to_prestashop.py -k KEY`
<pre>
Script importing categories, courses and images to PrestaShop

optional arguments:
  -h, --help         show this help message and exit
  
required arguments:
  -k KEY, --key KEY  Key for PrestaShop webservice
</pre>