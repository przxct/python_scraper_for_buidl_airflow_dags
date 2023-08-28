
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
    if response.status_code != 200:
        return []
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

    num_page = 1
    while True:
        next_page_url = base_url + str(num_page)

        # Break the loop if there are no more next pages
        # Crawl the next page
        new_list = crawl_page(next_page_url, section_css_selector)
        if len(new_list) == 0:
            break
        section_texts.append(new_list)
        num_page = num_page + 1
        # log data
        ti.log.info(f"Text from page {num_page}")
        ti.log.info(new_list)
    # for text in section_texts:
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
