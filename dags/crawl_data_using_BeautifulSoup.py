
from datetime import datetime, timedelta
from textwrap import dedent

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
# -----------------------------------------------------------------------------
import requests
from bs4 import BeautifulSoup
from airflow.operators.python_operator import PythonOperator

# --------------------------------- Crawl ---------------------------------------
def crawl_page(url, section_css_selector):
    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the section using the CSS selector
    section = soup.select_one(section_css_selector)

    # Extract the section text
    section_text = section.get_text()

    return section_text


def crawl_section_pages(ti):
    base_url = 'https://oj.vnoi.info/posts/'

    section_texts = []
    section_css_selector = '#blog-container > div.blog-content.sidebox > div.sidebox-content'

    # find number of pages of newfeeds
    response = requests.get(base_url + '1')
    soup = BeautifulSoup(response.text, 'html.parser')
    ultag = soup.find_all('ul', {'class': 'pagination'})[0]
    num_of_elements = len(ultag.find_all('li'))
    num_page = int(ultag.find_all('li')[num_of_elements-2].text)

    current_page = 1

    while current_page <= num_page:
        next_page_url = base_url + str(current_page)

        # Crawl the next page
        new_list = crawl_page(next_page_url, section_css_selector)
        section_texts.append(new_list)
        current_page = current_page + 1

        # log data
        if current_page == 5:
            ti.log.info(f"Text from page {current_page - 1}")
            ti.log.info(new_list)

    return section_texts


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 8, 28),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'website_crawler',
    default_args=default_args,
    # schedule_interval='0 3 * * *',
    schedule_interval='@daily',
    dagrun_timeout=timedelta(minutes=1)
)

crawl_task = PythonOperator(
    task_id='crawl_task',
    python_callable=crawl_section_pages,
    provide_context=True,  # Pass the task context to the function
    dag=dag
)
