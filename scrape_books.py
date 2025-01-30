import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore
import csv

url = 'http://127.0.0.1:5000'  

def scrape_books_to_csv():
    response = requests.get(url)
    
    if response.status_code != 200:
        print("Failed to retrieve the page")
        return

    soup = BeautifulSoup(response.content, 'html.parser')

    # Assuming the book items are in divs with the class 'book-item'
    books = soup.find_all('div', class_='book-item')

    books_data = []

    for book in books:
        try:
            title = book.find('h3', class_='book-title').get_text(strip=True)
            author = book.find('p', class_='book-author').get_text(strip=True)
            price = book.find('span', class_='book-price').get_text(strip=True)
            availability = book.find('span', class_='book-availability').get_text(strip=True)

            books_data.append([title, author, price, availability])

            # Optional: print data to check
            print(f"Title: {title}, Author: `{author}, Price: {price}, Availability: {availability}")
        except AttributeError:
            continue

    csv_filename = 'books_data.csv'

    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Author', 'Price', 'Availability'])
        writer.writerows(books_data)

    print(f"Scraping complete. Data saved to {csv_filename}")

scrape_books_to_csv()
