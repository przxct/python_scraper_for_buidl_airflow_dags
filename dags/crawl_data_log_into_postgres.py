
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
import logging
import os
import json
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


def list_post_id_in_newfeeds(soup):
    div_tag = soup.find("div", {'class': 'sidebox-content'})
    sections = div_tag.find_all('section')
    return sections


def get_fields_of_a_post(soup, section):
    # get id of section tag
    section_id = section.get('id')
    list_tag = soup.find("section", {'id': section_id})

    # post's title
    title = list_tag.find_all('h2')[0].text.strip()

    text = list_tag.find_all('span')[0].text
    author, date_time = text.split(" đã đăng vào ")

    # post's author
    author = author.strip()

    day, month, year, time = date_time.split(", ")
    date = ", ".join((day, month, year))

    # post's date
    date = date.strip()

    # post's time
    time = time.strip()

    # post's summary
    summary = list_tag.find_all("div", {'class': 'summary content-description blog-body'})[0].text

    return (title, author, date, time, summary)


def find_num_of_pages_of_newfeeds(base_url):
    response = requests.get(base_url + '1')
    soup = BeautifulSoup(response.text, 'html.parser')
    ultag = soup.find_all('ul', {'class': 'pagination'})[0]
    num_of_elements = len(ultag.find_all('li'))

    # handle exception num_page = 0
    if num_of_elements <= 2:
        return 0
    
    num_page = int(ultag.find_all('li')[num_of_elements-2].text)
    return num_page


def crawl_section_pages():
    base_url = 'https://oj.vnoi.info/posts/'

    # find number of pages of newfeeds
    num_page = find_num_of_pages_of_newfeeds(base_url)
    current_page = 1

    # esablish postgres connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_railway')

    postgres_insert_query = """ INSERT INTO test2(title, author, date, time, summary) 
                                VALUES (%s,%s,%s,%s,%s)"""

    while current_page <= num_page:
        next_page_url = base_url + str(current_page)
        response = requests.get(next_page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        sections = list_post_id_in_newfeeds(soup)

        for section in sections:
            new_row = get_fields_of_a_post(soup, section)
            # insert item to table
            logging.info(new_row)
            pg_hook.run(postgres_insert_query, parameters=new_row)

        current_page = current_page + 1


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

# create_data_table = PostgresOperator(
#     task_id="create_data_table",
#     postgres_conn_id="postgres_railway",
#     sql="sql/create_data_table.sql",
#     dag=dag
# )

# drop_table = PostgresOperator(
#     task_id="drop_table",
#     postgres_conn_id="postgres_railway",
#     sql="sql/drop_table.sql",
#     dag=dag
# )

# drop_table >> create_data_table >> crawl_task

